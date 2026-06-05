from http.server import BaseHTTPRequestHandler
import json, os

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_len))
        
        action = body.get('action', 'optimize')
        
        if action == 'optimize':
            result = self.optimize(body)
        elif action == 'parse':
            result = self.parse_resume(body)
        else:
            result = {"error": "Unknown action"}
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def optimize(self, body):
        import urllib.request
        
        sections = body.get('sections', [])
        api_key = os.environ.get('OPENAI_API_KEY', '')
        
        if not api_key:
            return {"error": "API key not configured", "results": []}
        
        results = []
        for section in sections:
            try:
                optimized = self.call_openai(api_key, section)
                results.append(optimized)
            except Exception as e:
                results.append({
                    "type": section.get('type', ''),
                    "original": section.get('content', ''),
                    "optimized": f"[优化失败: {str(e)}]",
                    "error": str(e)
                })
        
        return {"results": results}
    
    def call_openai(self, api_key, section):
        import urllib.request
        
        section_type = section.get('type', 'experience')
        content = section.get('content', '')
        
        prompts = {
            'summary': '你是一位资深HR和简历优化专家。请将以下个人概述改写得更专业、更有冲击力，突出核心竞争力。保持简洁，80字以内。直接输出改写结果，不要解释。\n\n原文：',
            'experience': '你是资深简历优化专家。将以下工作经历改写得更专业，使用强有力的动词开头（如：主导、设计、推动、优化），量化成果，突出影响力。每句话保持一行。直接输出改写结果，不要解释。\n\n原文：',
            'skills': '你是简历优化专家。将以下技能列表重新组织，按类别分组，突出核心技术栈。直接输出结果。\n\n原文：',
            'education': '你是简历优化专家。将以下教育背景格式化得更专业。直接输出结果。\n\n原文：',
            'project': '你是简历优化专家。将以下项目经历改写得更专业，突出技术亮点和个人贡献。直接输出结果。\n\n原文：',
        }
        
        prompt = prompts.get(section_type, prompts['experience']) + content
        
        data = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 600,
            "temperature": 0.7
        }).encode()
        
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        
        resp = urllib.request.urlopen(req, timeout=25)
        result = json.loads(resp.read())
        optimized = result['choices'][0]['message']['content'].strip()
        
        return {"type": section_type, "original": content, "optimized": optimized}
    
    def parse_resume(self, body):
        text = body.get('text', '')
        sections = []
        lines = text.split('\n')
        current_type = None
        current_content = []
        
        section_keywords = {
            'summary': ['个人概述', '个人简介', '自我评价', 'summary', 'profile', 'about me', '关于我'],
            'experience': ['工作经历', '工作经验', 'experience', 'work', 'employment'],
            'education': ['教育背景', '教育经历', 'education', '学历'],
            'skills': ['技能', '专业技能', '技术栈', 'skills', 'technologies'],
            'project': ['项目经验', '项目经历', 'projects', '项目'],
        }
        
        for line in lines:
            trimmed = line.strip()
            if not trimmed: continue
            
            found_section = None
            for sec_type, keywords in section_keywords.items():
                for kw in keywords:
                    if kw.lower() in trimmed.lower():
                        found_section = sec_type
                        break
                if found_section: break
            
            if found_section:
                if current_type and current_content:
                    sections.append({"type": current_type, "content": '\n'.join(current_content).strip()})
                current_type = found_section
                current_content = []
            elif current_type:
                current_content.append(trimmed)
        
        if current_type and current_content:
            sections.append({"type": current_type, "content": '\n'.join(current_content).strip()})
        
        return {"sections": sections}
