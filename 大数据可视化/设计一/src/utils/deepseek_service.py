from openai import OpenAI
import os
import sys
from src.utils.config import get_config

class DeepSeekService:
    def __init__(self):
        self.is_configured = False
        self._setup_service()

    def _load_api_key(self):
        try:
            return get_config("deepseek", "api_key", None)
        except Exception:
            return None

    def _setup_service(self):
        try:
            self.api_key = get_config("deepseek", "api_key", None)
            self.base_url = get_config("deepseek", "base_url", "https://api.deepseek.com")
            proxy = get_config("deepseek", "proxy", None)
            
            if proxy:
                os.environ["HTTP_PROXY"] = proxy
                os.environ["HTTPS_PROXY"] = proxy
                    
        except Exception:
            self.api_key = None
            self.base_url = "https://api.deepseek.com"

        if self.api_key and self.api_key != "YOUR_DEEPSEEK_API_KEY_HERE":
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            self.model = "deepseek-chat"
            self.is_configured = True
        else:
            self.is_configured = False

    def analyze_data(self, df_summary_str: str) -> str:
        """
        同步方法调用DeepSeek分析数据。
        注意：该方法会阻塞线程，必须在后台线程中调用。
        """
        # 每次调用时尝试重新加载，防止用户程序启动后才修改配置文件
        if not self.is_configured:
            self._setup_service()
            
        if not self.is_configured:
            return "错误：未配置有效的 DeepSeek API Key。请在 config.yaml 中填入您的 Key 后再次点击更新视图。"
        
        prompt = f"""
                    你是一位专业的环境数据分析师。以下是一段通过系统提取的核心空气质量数据总结（包含日期、城市、AQI、PM2.5、PM10、SO2、NO2 等信息）。
                    请你根据这段数据，提供一份专业的空气质量分析报告。
                    你需要包含以下方面：
                    1. **空气质量趋势总结**：这段时间内的整体趋势如何？
                    2. **异常值检测**：是否出现了严重的污染天数？或者有某项指标突然飙升？
                    3. **环境洞察与建议**：根据以上分析给出建议。

                    【数据如下】
                    {df_summary_str}

                    请用专业、清晰的中文进行总结。
                """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            if "proxy" in error_msg.lower() or "connection" in error_msg.lower() or "timeout" in error_msg.lower() or "10060" in error_msg:
                return (f"API 请求失败：网络连接异常 ({error_msg})。\n\n"
                        f"提示：请检查您的网络连接和代理设置。")
            return f"API 请求失败：{error_msg}"
