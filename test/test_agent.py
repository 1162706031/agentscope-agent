#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 后端测试脚本
测试认证、对话、流式对话、会话过期等功能
"""

import requests
import json
import time
import sys
from typing import Optional

# 配置
BASE_URL = "http://localhost:8080"
API_KEY = "sk-frontend-001"  # 使用你配置的前端认证 Key


class AgentTester:
    def __init__(self, base_url: str = BASE_URL, api_key: str = API_KEY):
        self.base_url = base_url
        self.api_key = api_key
        self.session_id = None
        self.test_results = []
    
    def print_test_result(self, test_name: str, passed: bool, message: str = ""):
        """打印测试结果"""
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")
        if message:
            print(f"     {message}")
        self.test_results.append({"name": test_name, "passed": passed, "message": message})
    
    def test_health_check(self):
        """测试1：健康检查"""
        print("\n📋 测试1：健康检查")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.print_test_result("健康检查", True, f"状态: {data.get('status')}")
                return True
            else:
                self.print_test_result("健康检查", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.print_test_result("健康检查", False, str(e))
            return False
    
    def test_auth(self):
        """测试2：认证 - 获取 session_id"""
        print("\n📋 测试2：认证")
        try:
            response = requests.post(
                f"{self.base_url}/auth",
                json={"api_key": self.api_key},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get("session_id")
                user_id = data.get("user_id")
                expires_at = data.get("expires_at")
                
                self.print_test_result(
                    "认证", 
                    True, 
                    f"session_id: {self.session_id[:8]}..., user_id: {user_id}"
                )
                return True
            else:
                self.print_test_result("认证", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.print_test_result("认证", False, str(e))
            return False
    
    def test_invalid_auth(self):
        """测试3：无效的 API Key 认证（应该失败）"""
        print("\n📋 测试3：无效 API Key 认证（预期失败）")
        try:
            response = requests.post(
                f"{self.base_url}/auth",
                json={"api_key": "invalid-key-123"},
                timeout=10
            )
            
            if response.status_code == 401:
                self.print_test_result("无效 Key 认证", True, "正确返回 401")
                return True
            else:
                self.print_test_result("无效 Key 认证", False, f"预期 401，实际 {response.status_code}")
                return False
        except Exception as e:
            self.print_test_result("无效 Key 认证", False, str(e))
            return False
    
    def test_chat(self):
        """测试4：普通对话"""
        print("\n📋 测试4：普通对话")
        if not self.session_id:
            self.print_test_result("普通对话", False, "没有有效的 session_id")
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/chat",
                json={
                    "session_id": self.session_id,
                    "message": "你好，请简单介绍一下你自己"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("content", "")
                self.print_test_result(
                    "普通对话", 
                    True, 
                    f"回复: {content[:50]}..."
                )
                return True
            else:
                self.print_test_result("普通对话", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.print_test_result("普通对话", False, str(e))
            return False
    
    def test_multi_turn_chat(self):
        """测试5：多轮对话"""
        print("\n📋 测试5：多轮对话")
        if not self.session_id:
            self.print_test_result("多轮对话", False, "没有有效的 session_id")
            return False
        
        conversations = [
            "我叫小明",
            "我刚才告诉你我叫什么名字？",
            "那你知道 Python 是什么吗？"
        ]
        
        try:
            for i, message in enumerate(conversations, 1):
                print(f"   第{i}轮: 用户 - {message}")
                
                response = requests.post(
                    f"{self.base_url}/chat",
                    json={
                        "session_id": self.session_id,
                        "message": message
                    },
                    timeout=30
                )
                
                if response.status_code != 200:
                    self.print_test_result("多轮对话", False, f"第{i}轮失败")
                    return False
                
                data = response.json()
                print(f"   第{i}轮: Agent - {data.get('content', '')[:60]}...")
            
            self.print_test_result("多轮对话", True, f"完成 {len(conversations)} 轮对话")
            return True
            
        except Exception as e:
            self.print_test_result("多轮对话", False, str(e))
            return False
    
    def test_stream_chat(self):
        """测试6：流式对话"""
        print("\n📋 测试6：流式对话")
        if not self.session_id:
            self.print_test_result("流式对话", False, "没有有效的 session_id")
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/stream",
                json={
                    "session_id": self.session_id,
                    "message": "给我讲一个很短的笑话"
                },
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                print("   流式输出: ", end="")
                full_content = ""
                for line in response.iter_lines():
                    if line:
                        decoded = line.decode('utf-8')
                        if decoded.startswith('data: '):
                            content = decoded[6:]
                            if content != '[DONE]':
                                print(content, end="", flush=True)
                                full_content += content
                print()  # 换行
                self.print_test_result("流式对话", True, f"完整回复长度: {len(full_content)}")
                return True
            else:
                self.print_test_result("流式对话", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.print_test_result("流式对话", False, str(e))
            return False
    
    def test_without_session(self):
        """测试7：不使用 session_id（应该失败）"""
        print("\n📋 测试7：无 session_id 请求（预期失败）")
        try:
            response = requests.post(
                f"{self.base_url}/chat",
                json={
                    "session_id": "invalid-session-id",
                    "message": "你好"
                },
                timeout=10
            )
            
            if response.status_code == 401:
                self.print_test_result("无 session_id", True, "正确返回 401")
                return True
            else:
                self.print_test_result("无 session_id", False, f"预期 401，实际 {response.status_code}")
                return False
        except Exception as e:
            self.print_test_result("无 session_id", False, str(e))
            return False
    
    def test_logout(self):
        """测试8：登出"""
        print("\n📋 测试8：登出")
        if not self.session_id:
            self.print_test_result("登出", False, "没有有效的 session_id")
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/logout",
                json={"session_id": self.session_id},
                timeout=10
            )
            
            if response.status_code == 200:
                self.print_test_result("登出", True, "Session 已销毁")
                self.session_id = None
                return True
            else:
                self.print_test_result("登出", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.print_test_result("登出", False, str(e))
            return False
    
    def test_session_reuse(self):
        """测试9：Session 复用（同一个 session_id 多次请求）"""
        print("\n📋 测试9：Session 复用测试")
        
        # 先认证获取 session_id
        auth_response = requests.post(
            f"{self.base_url}/auth",
            json={"api_key": self.api_key},
            timeout=10
        )
        
        if auth_response.status_code != 200:
            self.print_test_result("Session 复用", False, "认证失败")
            return False
        
        session_id = auth_response.json().get("session_id")
        
        # 发送多条消息，验证 Agent 状态是否保持
        messages = ["第一个问题", "第二个问题", "第三个问题"]
        
        try:
            for i, msg in enumerate(messages, 1):
                response = requests.post(
                    f"{self.base_url}/chat",
                    json={"session_id": session_id, "message": msg},
                    timeout=30
                )
                if response.status_code != 200:
                    self.print_test_result("Session 复用", False, f"第{i}条消息失败")
                    return False
            
            self.print_test_result("Session 复用", True, f"成功处理 {len(messages)} 条消息")
            return True
            
        except Exception as e:
            self.print_test_result("Session 复用", False, str(e))
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("🚀 开始测试 Agent 后端服务")
        print(f"📍 服务地址: {self.base_url}")
        print(f"🔑 API Key: {self.api_key}")
        print("="*60)
        
        # 检查服务是否可用
        if not self.test_health_check():
            print("\n❌ 服务不可用，请确保服务已启动")
            print("   启动命令: docker-compose up -d")
            sys.exit(1)
        
        # 运行所有测试
        self.test_invalid_auth()      # 测试无效认证
        self.test_auth()               # 测试认证
        self.test_chat()               # 测试普通对话
        self.test_stream_chat()        # 测试流式对话
        self.test_multi_turn_chat()    # 测试多轮对话
        self.test_session_reuse()      # 测试 Session 复用
        self.test_without_session()    # 测试无 session 请求
        self.test_logout()             # 测试登出
        
        # 打印总结
        self.print_summary()
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*60)
        print("📊 测试结果总结")
        print("="*60)
        
        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)
        
        for result in self.test_results:
            status = "✅" if result["passed"] else "❌"
            print(f"{status} {result['name']}")
            if result["message"]:
                print(f"   └─ {result['message']}")
        
        print("\n" + "-"*40)
        print(f"总计: {passed}/{total} 通过")
        
        if passed == total:
            print("\n🎉 所有测试通过！服务运行正常")
        else:
            print(f"\n⚠️ {total - passed} 个测试失败，请检查服务配置")
            sys.exit(1)


def quick_test():
    """快速单次测试（手动调用）"""
    print("快速测试模式")
    
    # 1. 健康检查
    print("\n1. 健康检查...")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"   {resp.json()}")
    
    # 2. 认证
    print("\n2. 认证...")
    resp = requests.post(f"{BASE_URL}/auth", json={"api_key": API_KEY})
    if resp.status_code == 200:
        session_id = resp.json()["session_id"]
        print(f"   Session ID: {session_id}")
        
        # 3. 对话
        print("\n3. 对话...")
        resp = requests.post(
            f"{BASE_URL}/chat",
            json={"session_id": session_id, "message": "你好"}
        )
        print(f"   回复: {resp.json()['content']}")
    else:
        print(f"   认证失败: {resp.text}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent 后端测试脚本")
    parser.add_argument("--url", default=BASE_URL, help="服务地址")
    parser.add_argument("--key", default=API_KEY, help="API Key")
    parser.add_argument("--quick", action="store_true", help="快速测试模式")
    
    args = parser.parse_args()
    
    if args.quick:
        BASE_URL = args.url
        API_KEY = args.key
        quick_test()
    else:
        tester = AgentTester(base_url=args.url, api_key=args.key)
        tester.run_all_tests()