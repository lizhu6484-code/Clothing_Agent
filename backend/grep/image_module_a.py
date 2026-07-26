import os
import random
import time
import requests
import re
import json
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from PIL import Image, ImageChops, ImageStat, ImageFilter
import dashscope
from urllib.parse import quote

# 确保默认物料路径存在
DEFAULT_IMAGE_PATH = "assets/materials/default.jpg"

class ImageProcessor:
    @staticmethod
    def crop_white_borders(image):
        """智能去白边 (Smart Crop) - 优化版，激进裁切以打破构图同质化"""
        if image.mode != "RGB":
            image = image.convert("RGB")
        bg = Image.new(image.mode, image.size, (255, 255, 255))
        diff = ImageChops.difference(image, bg)
        
        # 更加激进的阈值：颜色偏差在 40 以内的近似白边也抹为纯黑(背景)
        diff = diff.point(lambda p: 0 if p < 40 else p)
        bbox = diff.getbbox()
        
        if bbox:
            left, upper, right, lower = bbox
            w, h = image.size
            
            # Jitter 随机裁切干扰：向内额外收缩 0% ~ 4% 的像素，强制每张图边缘视觉不同
            left_shrink = int(w * random.uniform(0, 0.04))
            upper_shrink = int(h * random.uniform(0, 0.04))
            right_shrink = int(w * random.uniform(0, 0.04))
            lower_shrink = int(h * random.uniform(0, 0.04))
            
            left += left_shrink
            upper += upper_shrink
            right -= right_shrink
            lower -= lower_shrink
            
            if left < right and upper < lower:
                return image.crop((left, upper, right, lower))
            return image.crop(bbox)
            
        return image

    @staticmethod
    def calc_image_hash(image):
        """哈希校验: 生成 aHash (Average Hash) 简易指纹"""
        img = image.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
        pixels = list(img.getdata())
        avg = sum(pixels) / len(pixels)
        bits = "".join(['1' if p > avg else '0' for p in pixels])
        return int(bits, 2)

    @staticmethod
    def is_similar(hash1, hash2, threshold=5):
        """汉明距离算相似度，如果不同位 <= threshold，则认定高度相似"""
        diff = bin(hash1 ^ hash2).count('1')
        return diff <= threshold

    @staticmethod
    def check_skin_tone(image):
        """肤色过滤: >12%视为有人"""
        ycbcr_img = image.convert('YCbCr')
        sm_img = ycbcr_img.copy()
        sm_img.thumbnail((150, 150))
        w_sm, h_sm = sm_img.size
        
        skin_pixels = 0
        total_pixels = w_sm * h_sm
        for y in range(h_sm):
            for x in range(w_sm):
                pixel = sm_img.getpixel((x, y))
                y_val, cb, cr = pixel[0], pixel[1], pixel[2]
                if 77 <= cb <= 127 and 133 <= cr <= 173:
                    skin_pixels += 1
        return (skin_pixels / total_pixels) <= 0.12

    @staticmethod
    def check_sharpness(image):
        """计算拉普拉斯方差代表清晰度，返回方差值"""
        grayscale = image.convert('L')
        sm_img = grayscale.copy()
        sm_img.thumbnail((300, 300)) 
        edges = sm_img.filter(ImageFilter.FIND_EDGES)
        stat = ImageStat.Stat(edges)
        return stat.var[0]

    @staticmethod
    def check_size(image):
        w, h = image.size
        return w >= 200 and h >= 200
        
    @classmethod
    def validate_and_process(cls, img_data):
        try:
            image = Image.open(BytesIO(img_data))
            image.verify()
            image = Image.open(BytesIO(img_data))
            
            if not cls.check_size(image):
                return None
                
            variance = cls.check_sharpness(image)
            if variance < 50:
                return None
                
            if not cls.check_skin_tone(image):
                return None
            
            processed_img = cls.crop_white_borders(image)
            
            # 评分随机化：打破“同分同质”僵局
            base_score = variance
            random_weight = random.uniform(0, 0.5) * 100 
            final_score = base_score + random_weight
            
            return processed_img, final_score
        except Exception:
            return None


class Scraper:
    def __init__(self, keyword):
        self.keyword = keyword
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        }

    # 已知的非商品图片域名黑名单
    _BLOCKED_DOMAINS = [
        "baidu.com", "bcebos.com", "bdstatic.com", "emoji.", "douyinpic.com",
        "toutiao", "pstatp", "bing.com", "microsoft.com",
    ]

    @staticmethod
    def _clean_url(url):
        url = url.replace("\\/", "/").replace("\\\\/", "/").replace('\\"', '"')
        url = url.replace("\\u0026", "&").replace("&amp;", "&")
        if url.startswith("//"):
            url = "https:" + url
        return url.split('"')[0].split("'")[0].split(" ")[0].split("\\")[0].split("&quot")[0]

    @staticmethod
    def _extract_all_img_urls(html):
        candidates = set()
        # 1. 标准 <img> 标签的 src / data-src / original-src / data-original
        for attr in ['src', 'data-src', 'original-src', 'data-original', 'data-imgurl']:
            for m in re.findall(rf'{attr}\s*=\s*["\'](https?://[^"\']+)["\']', html, re.IGNORECASE):
                candidates.add(Scraper._clean_url(m))
        # 2. JSON 中的 url 字段 (thumbURL, objURL, middleURL, murl, imgurl, mediaurl 等)
        for key in ['thumbURL', 'objURL', 'middleURL', 'murl', 'imgurl', 'mediaurl', 'fromURL']:
            for m in re.findall(rf'"{key}"\s*:\s*"(https?://[^"]+)"', html):
                candidates.add(Scraper._clean_url(m))
        # 3. 任意带图片后缀的 URL
        for m in re.findall(r'(https?://[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}/[^"\'\\\s,<>]*\.(?:jpg|jpeg|png|webp)(?:\?[^"\'\\\s,<>]*)?)', html):
            candidates.add(Scraper._clean_url(m))
        # 4. onclick / onerror 属性中的 URL
        for m in re.findall(r'(?:onclick|onerror|onload)=["\'].*?(https?://[^"\'\\\s,]+\.(?:jpg|jpeg|png|webp)[^"\'\\\s]*)', html):
            candidates.add(Scraper._clean_url(m))
        # 5. CSS background-image url()
        for m in re.findall(r'background-image\s*:\s*url\(["\']?(https?://[^"\'\)]+)["\']?\)', html, re.IGNORECASE):
            candidates.add(Scraper._clean_url(m))
        # 过滤掉黑名单域名
        results = []
        for u in candidates:
            u_lower = u.lower()
            if any(blocked in u_lower for blocked in Scraper._BLOCKED_DOMAINS):
                continue
            if u.startswith("http") and len(u) > 20:
                results.append(u)
        return results

    def scrape_baidu(self):
        try:
            url = f"https://image.baidu.com/search/index?tn=baiduimage&word={quote(self.keyword)}"
            res = requests.get(url, headers=self.headers, timeout=8)
            return self._extract_all_img_urls(res.text)
        except:
            return []

    def scrape_bing(self):
        try:
            url = f"https://cn.bing.com/images/search?q={quote(self.keyword)}&FORM=IRFLTR"
            res = requests.get(url, headers=self.headers, timeout=8)
            return self._extract_all_img_urls(res.text)
        except:
            return []

    def scrape_unsplash(self):
        """LoremFlickr 免费图源（按关键词返回 Flickr 图片）"""
        try:
            kw_en = re.sub(r'[\u4e00-\u9fff]+', '', self.keyword).strip() or "product"
            url = f"https://loremflickr.com/800/800/{quote(kw_en)}"
            res = requests.get(url, headers=self.headers, timeout=8, allow_redirects=True)
            if res.status_code == 200 and len(res.content) > 5000:
                return [res.url]
        except:
            pass
        return []

    def download_image(self, url):
        cleaned = url.split("?")[0]  # 去 query 参数做近似去重
        if cleaned in Coordinator._seen_urls:
            return None
        try:
            res = requests.get(url, headers=self.headers, timeout=6)
            if res.status_code == 200:
                result = ImageProcessor.validate_and_process(res.content)
                if result:
                    img, score = result
                    return img, score, url
        except:
            pass
        return None

    def get_first_valid_image(self):
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            f1 = executor.submit(self.scrape_baidu)
            f2 = executor.submit(self.scrape_bing)
            f3 = executor.submit(self.scrape_unsplash)
            urls = [u for u in (f1.result() + f2.result() + f3.result()) if u]
            
        # 在这之前可能有很多无效或重复的内容
        urls = list(set(urls))
        urls = urls[:30]
        
        # 强制随机干扰：随机丢弃前 1~2 个元素
        drop_num = random.randint(1, 2)
        urls = urls[drop_num:]
        
        # 打乱随机性
        random.shuffle(urls)
        
        valid_results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(self.download_image, url): url for url in urls}
            for future in as_completed(futures):
                if time.time() - start_time > 15:
                    break
                res = future.result()
                if res:
                    img, score, valid_url = res
                    valid_results.append((score, img, valid_url))
                    # 收集几个候选结果从中挑分数最高(含随机权重)图
                    if len(valid_results) >= 5 or (time.time() - start_time > 8):
                        break

        if valid_results:
            valid_results.sort(key=lambda x: x[0], reverse=True)
            _, best_img, best_url = valid_results[0]
            return best_img, best_url
            
        return None


class Generator:
    def __init__(self, keyword):
        self.keyword = keyword
        self.api_key = os.getenv('DASHSCOPE_API_KEY')
        dashscope.api_key = self.api_key

    def generate_image(self):
        if not self.api_key:
            print("[Warning] 未设置 DASHSCOPE_API_KEY，跳过 AI 生图步骤。")
            return None
            
        # AI 生图的随机种子，加上当前时间作干扰防止万相同返回
        seed = random.randint(1000, 999999)
        prompt = f"{self.keyword}, 工业写实风格, 3D高精建模, 纯白背景 (white background), 专业商业摄影, 8k, 无人物, 无手部, 极简主义"
        try:
            rsp = dashscope.ImageSynthesis.call(
                model=dashscope.ImageSynthesis.Models.wanx_v1,
                prompt=prompt,
                n=1,
                size='1024*1024',
                seed=seed
            )
            if rsp.status_code == 200:
                url = rsp.output.results[0].url
                res = requests.get(url, timeout=5)
                if res.status_code == 200:
                    return Image.open(BytesIO(res.content))
        except Exception as e:
            print(f"AI 生成失败: {e}")
        return None


class Coordinator:
    # Session 级历史去重
    _seen_urls = set()
    _seen_hashes = set()
    _consecutive_dup_count = 0  # 连续重复/相似抓取计算

    def __init__(self, keyword):
        self.keyword = keyword

    def run(self):
        print(f"[{self.keyword}] 开始进入自动化物料获取流水线...")
        
        # 强制切换逻辑：如果已经连续 2 张图相似度过高，不再尝试，强制 AI
        if Coordinator._consecutive_dup_count >= 2:
            print(f"[{self.keyword}] 发现历史抓取图相似严重滞塞(连续 >= 2次)，直接强制触发 AI 生图打破同质化！")
            img = self.trigger_ai()
            # 成功触发 AI 后重置计数
            Coordinator._consecutive_dup_count = 0
            return img

        # 第一优先级：抓取
        start_time = time.time()
        scraper = Scraper(self.keyword)
        result = scraper.get_first_valid_image()
        
        if result and time.time() - start_time <= 15:
            img, url = result
            img_hash = ImageProcessor.calc_image_hash(img)
            
            # 图像后处理检测增强: 如果新图片指纹与之前的某个高度相似(不同<=5)，认定重复
            is_dup = any(ImageProcessor.is_similar(img_hash, sh) for sh in Coordinator._seen_hashes)
            
            if is_dup:
                print(f"[{self.keyword}] 警告：新抓取的图画与历史产出高度相似(哈希雷同)，拒绝应用！")
                Coordinator._consecutive_dup_count += 1
                
                if Coordinator._consecutive_dup_count >= 2:
                    print(f"[{self.keyword}] 连续 2 次抓去发生重复，马上触发 AI 生图接管...")
                    img = self.trigger_ai()
                    Coordinator._consecutive_dup_count = 0
                    return img
                else:
                    print(f"[{self.keyword}] 单次相似，本次退化为 AI 生成补救。")
                    return self.trigger_ai()
            else:
                # 全新有效图
                print(f"[{self.keyword}] 抓取成功！全新且校验完备的图。耗时: {time.time() - start_time:.2f}s")
                Coordinator._seen_urls.add(url)
                Coordinator._seen_hashes.add(img_hash)
                Coordinator._consecutive_dup_count = 0
                return img
            
        # 抓取耗时超 10s 或未获取到合格图片
        print(f"[{self.keyword}] 抓取未获取有效信息(或全部过滤)，切换 AI 生图...")
        return self.trigger_ai()

    def trigger_ai(self):
        generator = Generator(self.keyword)
        img = generator.generate_image()
        if img:
            print(f"[{self.keyword}] AI 生成成功！")
            img = ImageProcessor.crop_white_borders(img)
            # 同样记录 AI 生图的 hash
            img_hash = ImageProcessor.calc_image_hash(img)
            Coordinator._seen_hashes.add(img_hash)
            return img
            
        print(f"[{self.keyword}] API 调用失败，执行最终兜底返回默认图片...")
        return self._get_default_image()

    def _get_default_image(self):
        if os.path.exists(DEFAULT_IMAGE_PATH):
            return Image.open(DEFAULT_IMAGE_PATH)
        os.makedirs(os.path.dirname(DEFAULT_IMAGE_PATH), exist_ok=True)
        img = Image.new('RGB', (800, 800), color=(240, 240, 240))
        img.save(DEFAULT_IMAGE_PATH)
        return img


def get_material_image_path_a(keyword):
    coordinator = Coordinator(keyword)
    img = coordinator.run()
    if img:
        save_dir = "output"
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f"{keyword}_{int(time.time())}.jpg")
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        img.save(path, "JPEG", quality=95)
        return os.path.abspath(path)
        
    return None

if __name__ == "__main__":
    result_path = get_material_image_path_a("液压泵")
    print(f"-> 最终输出产物路径: {result_path}")
