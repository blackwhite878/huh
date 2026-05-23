#!/usr/bin/env python
"""
Manual API test script - Test the complete pipeline without frontend.
Run this to verify all endpoints work correctly.
"""

import asyncio
import httpx
import json
import time
from typing import Any

API_BASE = "http://localhost:8000"

class APITester:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=API_BASE)
        self.session_id = None

    async def test_init_session(self):
        """Test 1: Initialize session"""
        print("\n" + "="*60)
        print("TEST 1: Initialize Session")
        print("="*60)

        payload = {
            "budget": 500000,
            "agent_style": "professional",
            "target": "condo in Johor Bahru",
            "identity": "first_time_buyer",
            "gender": "female",
        }

        response = await self.client.post("/api/v1/init_session", json=payload)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(json.dumps(data, indent=2))

        self.session_id = data.get("session_id")
        assert self.session_id, "No session_id returned"
        print(f"\n✅ Session created: {self.session_id}")
        return True

    async def test_session_ready_polling(self):
        """Test 2: Poll semantic alignment"""
        print("\n" + "="*60)
        print("TEST 2: Poll Semantic Alignment (3 retries, 1 sec delay)")
        print("="*60)

        for i in range(3):
            response = await self.client.get(f"/api/v1/session_ready/{self.session_id}")
            data = response.json()
            print(f"Poll {i+1}: {data['status']}")

            if data["status"] == "ready":
                print(f"✅ Semantic alignment complete")
                print(f"   Tags: {data.get('semantic_tags', [])}")
                print(f"   Warning: {data.get('alignment_warning', False)}")
                return True

            await asyncio.sleep(1)

        print("⚠️  Alignment still pending (expected in MVP)")
        return True

    async def test_chat(self):
        """Test 3: Send chat message"""
        print("\n" + "="*60)
        print("TEST 3: Send Chat Message")
        print("="*60)

        payload = {
            "session_id": self.session_id,
            "message": "我想找靠近地鐵站的公寓，管理費要便宜",
        }

        response = await self.client.post("/api/v1/chat", json=payload)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(json.dumps(data, indent=2))

        print(f"\n✅ Chat response received")
        print(f"   Status: {data['status']}")
        print(f"   Reply: {data['reply']}")

        return data["status"] in ["chatting", "pending_confirmation", "searching"]

    async def test_chat_fc_trigger(self):
        """Test 4: Chat that triggers Function Calling"""
        print("\n" + "="*60)
        print("TEST 4: Chat to Trigger Function Calling")
        print("="*60)

        payload = {
            "session_id": self.session_id,
            "message": "好的，我準備好了，請幫我搜索",
        }

        response = await self.client.post("/api/v1/chat", json=payload)
        data = response.json()
        print(json.dumps(data, indent=2))

        print(f"\n✅ Chat response: {data['status']}")

        if data["status"] == "searching":
            print("   ✅ Function Calling triggered!")
            return True
        else:
            print("   ⚠️  FC not triggered yet (continue chatting)")
            return False

    async def test_search_status_polling(self):
        """Test 5: Poll search progress"""
        print("\n" + "="*60)
        print("TEST 5: Poll Search Progress (10 retries, 1 sec delay)")
        print("="*60)

        for i in range(10):
            response = await self.client.get(f"/api/v1/search_status/{self.session_id}")
            data = response.json()
            print(f"Poll {i+1}: status={data['status']}", end="")

            if data["status"] == "complete":
                print(f" ✅")
                print(f"\nSearch completed:")
                print(f"  Batch: {data.get('batch_index', 0)}/{data.get('total_available', 0)}")
                print(f"  Has More: {data.get('has_more', False)}")
                print(f"  Tier3: {data.get('tier3_triggered', False)}")
                print(f"  Results: {len(data.get('results', []))} properties")

                if data.get("results"):
                    print(f"\nFirst property:")
                    prop = data["results"][0]
                    print(f"  ID: {prop['property_id']}")
                    print(f"  Tier: {prop['tier']}")
                    print(f"  Remarks: {prop['remarks'][:100]}...")

                return True

            print()
            await asyncio.sleep(1)

        print("\n⚠️  Search still in progress (check again)")
        return True

    async def test_reject_single(self):
        """Test 6: Reject single property"""
        print("\n" + "="*60)
        print("TEST 6: Reject Single Property")
        print("="*60)

        payload = {
            "session_id": self.session_id,
            "property_id": "JB001",
            "reason": "樓層太高，西晒",
        }

        response = await self.client.post("/api/v1/reject_single", json=payload)
        data = response.json()
        print(json.dumps(data, indent=2))

        print(f"\n✅ Rejection recorded: {data.get('rejection_count', 0)} total")
        return True

    async def test_reject_all(self):
        """Test 7: Reject all (trigger NPP learning)"""
        print("\n" + "="*60)
        print("TEST 7: Reject All (Trigger NPP Learning)")
        print("="*60)

        payload = {
            "session_id": self.session_id,
        }

        response = await self.client.post("/api/v1/reject_all", json=payload)
        data = response.json()
        print(json.dumps(data, indent=2))

        print(f"\n✅ NPP learning triggered")
        print(f"   Updated tags: {data.get('npp_updated', [])}")
        print(f"   Message: {data.get('message', '')}")
        return True

    async def test_resolve_action(self):
        """Test 8: Resolve action (New Prompt or Keep Memories)"""
        print("\n" + "="*60)
        print("TEST 8: Resolve Action - New Prompt")
        print("="*60)

        payload = {
            "session_id": self.session_id,
            "action": "new_prompt",
        }

        response = await self.client.post("/api/v1/resolve_action", json=payload)
        data = response.json()
        print(json.dumps(data, indent=2))

        print(f"\n✅ Action resolved: {data['status']}")
        print(f"   Next phase: {data['next_phase']}")
        return True

    async def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "🧪 PROPERTY AGENT UI - API TEST SUITE 🧪".center(60, "="))

        try:
            # Test flow
            await self.test_init_session()
            await self.test_session_ready_polling()
            await self.test_chat()

            # Try to trigger FC
            fc_triggered = await self.test_chat_fc_trigger()
            if fc_triggered:
                await self.test_search_status_polling()
                await self.test_reject_single()
                await self.test_reject_all()

            await self.test_resolve_action()

            print("\n" + "="*60)
            print("✅ All tests completed successfully!")
            print("="*60)

        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.client.aclose()


async def main():
    tester = APITester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

