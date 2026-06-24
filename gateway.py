"""
通用 ASGI 网关中间件 (Generic ASGI Gateway Middleware)
======================================================
已合并：
- 首页 / /panel /memory 返回 index.html
- OpenAI 兼容代理 /v1/chat/completions /v1/models
- MCP 鉴权 /sse /messages /api/*
- 记忆面板后端 API /api/panel/*
"""

import os
import json
import asyncio
import time
import datetime
import requests

_supabase_client = None
_mem0_client = None
_system_logs_buffer = []
_MAX_LOGS = logdatetimeM:%S')}] {msg}"
    print(line, flush=True)
    _system_logs_buffer.append(line)
    if len(_system_logs_buffer) > _MAX_LOGS:
        del _system_logs_buffer[: len(_system_logs_buffer) - _MAX_LOGS]


def _get_supabase():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_KEY", "").strip()
    if not url or not key:
        return None
    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
        _log(f"✅ Supabase 已连接: {url[:30]}...")
    except Exception as e:
        _log(f"❌ Supabase 连接失败: {e}")
        _supabase_client = None
    return _supabase_client


def _get_mem0():
    global _mem0_client
    if _mem0_client is not None:
        return _mem0_client
    api_key = os.environ.get("MEM0_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from mem0 import Memory
        _mem0_client = Memory()
        _log("✅ Mem0 已初始化")
    except Exception as e:
        _log(f"❌ Mem0 初始化失败（将跳过向量记忆）: {e}")
        _mem0_client = None
    return _mem0_client


class HostFixMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket" and scope["path"] == "/qq-ws":
            try:
                import napcat
                await napcat.handle_napcat_ws(scope, receive, send)
            except Exception as e:
                _log(f"❌ NapCat WS 处理异常: {e}")
            return

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope["path"] in ("/", "/panel", "/memory"):
            try:
                here = os.path.dirname(os.path.abspath__)) with.path,.htmlrb f body.read awaittypehttp", nheaders" b/html; charset=utf-8")]})
                await send({"type": "http.response.body", "body": body})
            except Exception as e:
                html = "<h1>面板未找到</h1><p>请确认 index.html 已上传到仓库根目录，并且 Dockerfile 已 COPY index.html。</p><pre>" + str(e) + "</pre>"
                await send({"type": "http.response.start", "status": 500,
                            "headers": [(b"content-type", b"text/html; charset=utf-8")]})
                await send({"type": "http.response.body", "body": html.encode("utf-8")})
            return

        if scope["path"] == "/health":
            await _send_json_resp(send, 200, {"status": "ok", "service": "generic-mcp-gateway"})
            return

        if scope["path"].startswith("/v1/"):
            if scope["method"] == "OPTIONS":
                await _send_cors_preflight(send)
                return
            await self._handle_openai_proxy(scope, receive, send)
            return

        if (scope["path"].startswith("/api/") or scope["path"].startswith("/sse") or scope["path"].startswith("/messages")) and scope["method"] != "OPTIONS":
            if not await _check_api_secret(scope, send):
                return

        if scope["method"] == "OPTIONS":
            await _send_cors_preflight(send)
            return

        if scope["path"].startswith("/api/panel/"):
            await self._handle_panel_api(scope, receive, send)
            return

        if scope["path"] == "/api/logs":
            await self._handle_logs(send)
            return

        headers = dict(scope.get("headers", []))
        headers[b"host"] = b"localhost:8000"
        scope["headers"] = list(headers.items())
        await self.app(scope, receive, send)

    async def _handle_openai_proxy(self, scope, receive, send):
        path = scope["path"]
        method = scope["method"]
        api_secret = os.environ.get("API_SECRET", "").strip()
        if api_secret:
            if not await _check_api_secret(scope, send):
                return

        if path == "/v1/models" and method == "GET":
            default_model = os.environ.get("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
            models = [{"id": default_model, "object": "model", "created": int(time.time()), "owned_by": "mcp-gateway"}]
            for prefix in ("CHAT_", "SILICON1_", "VISION_", "VOICE_"):
                mn = os.environ.get(f"{prefix}MODEL_NAME", "").strip()
                if mn and mn != default_model:
                    models.append({"id": mn, "object": "model", "created": int(time.time()), "owned_by": "mcp-gateway"})
            await _send_json_resp(send, 200, {"object": "list", "data": models})
            return

        if path == "/v1/chat/completions" and method == "POST":
            await self._handle_chat(scope, receive, send)
            return

        await _send_json_resp(send, 404, {"error": {"message": f"Unknown endpoint: {path}"}})

    async def _handle_chat(self, scope, receive, send):
        body = b""
        while True:
            msg = await receive()
            body += msg.get("body", b"")
            if not msg.get("more_body", False):
                break

        try:
            req_data = json.loads(body.decode("utf-8"))
        except Exception:
            await _send_json_resp(send, 400, {"error": {"message": "Invalid JSON body"}})
            return

        upstream_base = os.environ.get("OPENAI_BASE_URL", os.environ.get("CHAT_BASE_URL", os.environ.get("DEFAULT_BASE_URL", ""))).strip()
        upstream_key = os.environ.get("OPENAI_API_KEY", os.environ.get("CHAT_API_KEY", os.environ.get("DEFAULT_API_KEY", ""))).strip()
        default_model = os.environ.get("OPENAI_MODEL_NAME", os.environ.get("CHAT_MODEL_NAME", os.environ.get("DEFAULT_MODEL_NAME", "gpt-3.5-turbo")))

        if not upstream_key:
            await _send_json_resp(send, 500, {"error": {"message": "Server 未配置 OPENAI_API_KEY"}})
            return

        if not req_data.get("model"):
            req_data["model"] = default_model

        base = upstream_base.rstrip("/") or "https://api.openai.com/v1"
        upstream_url = f"{base}/chat/completions" if base.endswith("/v1") else f"{base}/v1/chat/completions"

        sb = _get_supabase()
        user_msg = ""
        for m in reversed(req_data.get("messages", [])):
            if m.get("role") == "user":
                user_msg = str(m.get("content", ""))
                break

        if sb and user_msg:
            try:
                await self._inject_context(req_data, sb, user_msg)
            except Exception as e:
                _log(f"⚠️ 上文注入失败（已降级为透传）: {e}")

        req_data["stream"] = True
        if req_data.get("tools"):
            req_data["tool_choice"] = "auto"

        client_headers = {k.decode("utf-8", "ignore").lower(): v.decode("utf-8", "ignore") for k, v in scope.get("headers", [])}
        client_ua = client_headers.get("user-agent", "")
        fwd_headers = {
            "Authorization": f"Bearer {upstream_key}",
            "Content-Type": "application/json",
            "User-Agent": client_ua or "Mozilla/5.0",
            "Accept": client_headers.get("accept", "application/json"),
        }
        for h in ("accept-language", "x-requested-with"):
            if h in client_headers:
                fwd_headers[h] = client_headers[h]

        _log(f"➡️ [转发] POST {upstream_url} | model={req_data.get('model')} | key={upstream_key[:6]}***")

        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"text/event-stream; charset=utf-8"),
                (b"cache-control", b"no-cache"),
                (b"connection", b"keep-alive"),
                (b"access-control-allow-origin", b"*"),
            ],
        })

        import queue
        import threading
        q = queue.Queue()

        def _stream_forward():
            try:
                fwd_headers["Connection"] = "keep-alive"
                with requests.post(upstream_url, headers=fwd_headers, json=req_data, stream=True, timeout=300) as resp:
                    if resp.status_code != 200:
                        q.put({"error": f"HTTP {resp.status_code}: {resp.text[:500]}"})
                        q.put(None)
                        return
                    for line in resp.iter_lines():
                        if line:
                            q.put(line.decode("utf-8"))
                q.put(None)
            except Exception as e:
                q.put({"error": str(e)})
                q.put(None)

        threading.Thread(target=_stream_forward, daemon=True).start()

        collected_content = ""
        collected_reasoning = ""
        tool_calls_dict = {}

        while True:
            chunk = await asyncio.to_thread(q.get)
            if chunk is None:
                break

            if isinstance(chunk, dict) and "error" in chunk:
                _log(f"❌ 上游流式报错: {chunk['error']}")
                err_chunk = {
                    "id": "chatcmpl-error",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": req_data.get("model"),
                    "choices": [{"index": 0, "delta": {"content": f"\n\n[上游错误] {chunk['error']}"}, "finish_reason": "stop"}],
                }
                await send({"type": "http.response.body", "body": f"data: {json.dumps(err_chunk, ensure_ascii=False)}\n\n".encode("utf-8"), "more_body": True})
                continue

            await send({"type": "http.response.body", "body": (chunk + "\n\n").encode("utf-8"), "more_body": True})

            if chunk.startswith("data: ") and chunk != "data: [DONE]":
                try:
                    dj = json.loads(chunk[6:])
                    if dj.get("choices"):
                        delta = dj["choices"][0].get("delta", {})
                        if delta.get("content"):
                            collected_content += delta["content"]
                        if delta.get("reasoning_content"):
                            collected_reasoning += delta["reasoning_content"]
                        if delta.get("tool_calls"):
                            for tc in delta["tool_calls"]:
                                idx = tc.get("index", 0)
                                if idx not in tool_calls_dict:
                                    tool_calls_dict[idx] = tc
                                else:
                                    if tc.get("function", {}).get("arguments"):
                                        tool_calls_dict[idx]["function"].setdefault("arguments", "")
                                        tool_calls_dict[idx]["function"]["arguments"] += tc["function"]["arguments"]
                except Exception:
                    pass

        await send({"type": "http.response.body", "body": b"", "more_body": False})

        if sb and user_msg and (collected_content or tool_calls_dict):
            asyncio.create_task(self._save_conversation(sb, user_msg, collected_content, collected_reasoning, tool_calls_dict))

    async def _inject_context(self, req_data, sb, current_query):
        ai_name = os.environ.get("AI_NAME", "助手")
        user_name = os.environ.get("USER_NAME", "用户")
        user_id = os.environ.get("USER_ID", "default")
        persona = os.environ.get("AI_PERSONA", "").strip()
        chat_tag = os.environ.get("CHAT_TAG", "Web_Chat")
        now_bj = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        time_str = now_bj.strftime("%Y-%m-%d %H:%M")

        silence_hours = 0
        try:
            res = await asyncio.to_thread(lambda: sb.table("memories").select("created_at").eq("tags", chat_tag).order("created_at", desc=True).limit(1).execute())
            if res and res.data:
                last = res.data[0].get("created_at", "")
                if last:
                    try:
                        last_dt = datetime.datetime.strptime(last[:19], "%Y-%m-%dT%H:%M:%S")
                        silence_hours = max(0, round((now_bj - (last_dt + datetime.timedelta(hours=8))).total_seconds() / 3600, 1))
                    except Exception:
                        pass
        except Exception:
            pass

        core_summaries = "无长期记忆"
        try:
            sr = await asyncio.to_thread(lambda: sb.table("memories").select("content").eq("tags", "Core_Cognition").order("created_at", desc=True).limit(3).execute())
            if sr and sr.data:
                core_summaries = "\n".join([f"- {s['content']}" for s in sr.data])
        except Exception:
            pass

        user_prof = "暂无"
        try:
            pr = await asyncio.to_thread(lambda: sb.table("user_facts").select("key, value").neq("key", "sys_config").neq("key", "llm_settings").execute())
            if pr and pr.data:
                user_prof = "\n".join([f"- {r['key']}: {str(r['value'])[:200]}" for r in pr.data[:30]])
        except Exception:
            pass

        mem0_context = "无相关深层记忆"
        mc = _get_mem0()
        if mc and current_query.strip():
            try:
                def _s():
                    return mc.search(query=str(current_query), user_id=user_id, filters={"user_id": user_id}, limit=5)
                mr = await asyncio.to_thread(_s)
                if mr:
                    rl = mr.get("results", mr) if isinstance(mr, dict) else mr
                    if isinstance(rl, list) and rl:
                        mem0_context = "\n".join([f"- {m.get('memory', str(m))}" if isinstance(m, dict) else f"- {str(m)}" for m in rl])
            except Exception as e:
                _log(f"Mem0 检索失败（跳过）: {e}")

        history_msgs = []
        try:
            tags = [chat_tag, "TG_MSG", "QQ_Chat", "QQ_Group", "Email_Process"]
            hr = await asyncio.to_thread(lambda: sb.table("memories").select("content, tags").in_("tags", tags).order("created_at", desc=True).limit(20).execute())
            if hr and hr.data:
                rows = list(reversed(hr.data))[-10:]
                for row in rows:
                    c = str(row.get("content", "")).strip()
                    if not c:
                        continue
                    if c.startswith(user_name):
                        history_msgs.append({"role": "user", "content": (c.split("：", 1)[-1] if "：" in c else c)[:500]})
                    elif c.startswith("我(") or c.startswith(f"我({ai_name})"):
                        history_msgs.append({"role": "assistant", "content": (c.split("：", 1)[-1] if "：" in c else c)[:500]})
                merged = []
                for m in history_msgs:
                    if merged and merged[-1]["role"] == m["role"]:
                        merged[-1]["content"] += "\n" + m["content"]
                    else:
                        merged.append(m)
                history_msgs = merged
                while history_msgs and history_msgs[0]["role"] != "user":
                    history_msgs.pop(0)
        except Exception as e:
            _log(f"拉取上文失败（跳过）: {e}")

        status_inject = (
            f"\n\n[系统当前状态]\n当前时间:{time_str}(北京时间),距离上次聊天:{silence_hours}h。\n"
            f"【{user_name}的核心画像】:\n{user_prof}\n\n"
            f"--- 以下为调取的历史背景记忆（请注意这是过去的事，不是现在正在聊的内容） ---\n"
            f"【深层关联记忆】:\n{mem0_context}\n"
            f"【近3次阶段总结】:\n{core_summaries}\n"
            f"------------------------------------------------\n"
        )
        if persona:
            status_inject = f"{persona}\n{status_inject}"

        has_system = False
        for m in req_data.get("messages", []):
            if m.get("role") == "system":
                m["content"] = str(m.get("content", "")) + status_inject
                has_system = True
                break
        if not has_system and req_data.get("messages"):
            req_data["messages"].insert(0, {"role": "system", "content": status_inject.strip()})

        while req_data.get("messages") and req_data["messages"][-1].get("role") == "assistant":
            req_data["messages"].pop()

        if history_msgs:
            sys_idx = 0
            for i, m in enumerate(req_data["messages"]):
                if m.get("role") == "system":
                    sys_idx = i + 1
                    break
            for j, hm in enumerate(history_msgs):
                req_data["messages"].insert(sys_idx + j, hm)

        _log(f"🧠 [智能体] 注入完成：画像{len(user_prof)}字 + 总结{len(core_summaries)}字 + Mem0{len(mem0_context)}字 + 上文{len(history_msgs)}条")

    async def _save_conversation(self, sb, user_msg, ai_msg, reasoning, tool_calls):
        ai_name = os.environ.get("AI_NAME", "助手")
        user_name = os.environ.get("USER_NAME", "用户")
        user_id = os.environ.get("USER_ID", "default")
        chat_tag = os.environ.get("CHAT_TAG", "Web_Chat")
        now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        final_save_text = ai_msg
        if reasoning:
            final_save_text = f"<think>\n{reasoning}\n</think>\n\n{final_save_text}"
        if not final_save_text and tool_calls:
            tc_names = [tc.get("function", {}).get("name", "unknown") for tc in tool_calls.values()]
            final_save_text = f"[系统记录：调用了工具 {', '.join(tc_names)}]"

        try:
            def _save_user():
                sb.table("memories").insert({
                    "title": f"💬 {user_name}说",
                    "content": f"{user_name}：{user_msg[:2000]}",
                    "category": "流水",
                    "mood": "平静",
                    "tags": chat_tag,
                    "created_at": now_str,
                }).execute()
            await asyncio.to_thread(_save_user)

            def _save_ai():
                sb.table("memories").insert({
                    "title": f"🤖 {ai_name}回复",
                    "content": f"我({ai_name})：{final_save_text[:2000]}",
                    "category": "流水",
                    "mood": "温和",
                    "tags": chat_tag,
                    "created_at": now_str,
                }).execute()
            await asyncio.to_thread(_save_ai)
            _log(f"💾 已存库：{user_name}问({len(user_msg)}字) + {ai_name}答({len(final_save_text)}字)")
        except Exception as e:
            _log(f"❌ 存库失败: {e}")

        mc = _get_mem0()
        if mc and user_msg:
            try:
                def _add_m():
                    mc.add([
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": final_save_text},
                    ], user_id=user_id)
                await asyncio.to_thread(_add_m)
                _log("🧠 Mem0 已写入")
            except Exception as e:
                _log(f"Mem0 写入失败: {e}")

    async def _handle_panel_api(self, scope, receive, send):
        from urllib.parse import parse_qs
        sb = _get_supabase()
        if not sb:
            await _send_json_resp(send, 500, {"ok": False, "error": "Supabase 未连接"})
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET").upper()
        query = parse_qs(scope.get("query_string", b"").decode("utf-8", "ignore"))

        def q(name, default=""):
            v = query.get(name, [default])
            return v[0] if v else default

        async def read_body_json():
            body = b""
            while True:
                msg = await receive()
                body += msg.get("body", b"")
                if not msg.get("more_body", False):
                    break
            if not body:
                return {}
            try:
                return json.loads(body.decode("utf-8"))
            except Exception:
                return {}

        def is_uuid_like(s):
            import re
            return bool(re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", str(s or "").strip()))

        def hidden_persona(name):
            s = str(name or "").strip()
            low = s.lower()
            if not s:
                return True
            if is_uuid_like(s):
                return True
            blocked = ["diagnose", "debug", "manual", "unknown", "未映射", "kiro"]
            return any(x in low for x in blocked)

        def table_for_kind(kind):
            return "chat_archive" if kind == "archive" else "chat_messages"

        try:
            if path == "/api/panel/personas" and method == "GET":
                def _fetch_personas():
                    return sb.table("personas").select("persona_name,display_name,enabled,sort_order").eq("enabled", True).order("sort_order").limit(200).execute().data
                rows = await asyncio.to_thread(_fetch_personas)
                rows = [r for r in (rows or []) if not hidden_persona(r.get("persona_name"))]
                wanted = {"默认助手", "默认助手_技术线", "骆云影_联姻线", "测试助手"}
                rows = [r for r in rows if r.get("persona_name") in wanted or r.get("display_name") in wanted]
                await _send_json_resp(send, 200, {"ok": True, "data": rows})
                return

            if path == "/api/panel/records" and method == "GET":
                kind = q("kind", "memory")
                table = table_for_kind(kind)
                persona = q("persona", "").strip()
                keyword = q("keyword", "").strip()
                category = q("category", "").strip()
                role = q("role", "").strip()
                page = max(1, int(q("page", "1") or "1"))
                page_size = max(1, min(100, int(q("page_size", "20") or "20")))
                start = (page - 1) * page_size
                end = start + page_size - 1

                def _fetch_records():
                    query_obj = sb.table(table).select("id,assistant_id,conversation_id="                    if category query_obj.eq("category", category)
                    if role and kind == "archive":
                        query_obj = query_obj.eq("role", role)
                    if keyword:
                        query_obj = query_obj.ilike("content", f"%{keyword}%")
                    res = query_obj.order("created_at", desc=True).range(start, end).execute()
                    return res.data or [], getattr(res, "count", None)

                rows, total = await asyncio.to_thread(_fetch_records)
                if total is None:
                    total = len(rows)
                await _send_json_resp(send, 200, {"ok": True, "data": rows, "total": total, "page": page, "page_size": page_size})
                return

            if path == "/api/panel/record" and method == "POST":
                data = await read_body_json()
                kind = str(data.get("kind") or "memory")
                table = table_for_kind(kind)
                persona = str(data.get("persona_name") or "").strip()
                content = str(data.get("content") or "").strip()
                category = str(data.get("category") or "").strip()
                role = str(data.get("role") or ("user" if kind == "archive" else "system")).strip()
                conversation_id = str(data.get("conversation_id") or "manual").strip()
                if not persona:
                    await _send_json_resp(send, 400, {"ok": False, "error": "缺少 persona_name"})
                    return
                if not content:
                    await _send_json_resp(send, 400, {"ok": False, "error": "缺少 content"})
                    return
                if kind != "archive":
                    clean_cat = category or "剧情"
                    if not content.startswith("["):
                        content = f"[{clean_cat}] {content}"
                row = {
                    "assistant_id": persona,
                    "conversation_id": conversation_id,
                    "role": role,
                    "content": content,
                    "category": category or ("archive" if kind == "archive" else "剧情"),
                }
                def _insert():
                    return sb.table(table).insert(row).execute().data
                inserted = await asyncio.to_thread(_insert)
                await _send_json_resp(send, 200, {"ok": True, "data": inserted})
                return

            if path == "/api/panel/record" and method == "PATCH":
                data = await read_body_json()
                kind = str(data.get("kind") or "memory")
                table = table_for_kind(kind)
                rid = str(data.get("id") or "").strip()
                if not rid:
                    await _send_json_resp(send, 400, {"ok": False, "error": "缺少 id"})
                    return
                update_data = {}
                for key in ["assistant_id", "conversation_id", "role", "content", "category"]:
                    if key in data:
                        update_data[key] = data[key]
                if "persona_name" in data:
                    update_data["assistant_id"] = data["persona_name"]
                if not update_data:
                    await _send_json_resp(send, 400, {"ok": False, "error": "没有可更新字段"})
                    return
                def _update():
                    return sb.table(table).update(update_data).eq("id", rid).execute().data
                updated = await asyncio.to_thread(_update)
                await _send_json_resp(send, 200, {"ok": True, "data": updated})
                return

            if path == "/api/panel/record" and method == "DELETE":
                data = await read_body_json()
                kind = str(data.get("kind") or "memory")
                table = table_for_kind(kind)
                rid = str(data.get("id") or "").strip()
                if not rid:
                    await _send_json_resp(send, 400, {"ok": False, "error": "缺少 id"})
                    return
                def _delete():
                    return sb.table(table).delete().eq("id", rid).execute().data
                deleted = await asyncio.to_thread(_delete)
                await _send_json_resp(send, 200, {"ok": True, "data": deleted})
                return

            await _send_json_resp(send, 404, {"ok": False, "error": "未知 panel API"})
            return

        except Exception as e:
            _log(f"❌ Panel API 错误: {e}")
            await _send_json_resp(send, 500, {"ok": False, "error": str(e)})
            return

    async def _handle_logs(self, send):
        try:
            await _send_json_resp(send, 200, {"logs": "\n".join(_system_logs_buffer[-100:])})
        except Exception as e:
            await _send_json_resp(send, 500, {"error": str(e)})


async def _check_api_secret(scope, send):
    api_secret = os.environ.get("API_SECRET", "").strip()
    if not api_secret:
        return True
    headers_dict = {k.decode("utf-8").lower(): v.decode("utf-8") for k, v in scope.get("headers", [])}
    auth_token = headers_dict.get("authorization", "").replace("Bearer ", "").replace("bearer ", "").strip()
    x_api_key = headers_dict.get("x-api-key", "").strip()
    if auth_token != api_secret and x_api_key != api_secret:
        await send({"type": "http.response.start", "status": 401,
                    "headers": [(b"content-type", b"application/json"), (b"access-control-allow-origin", b"*")]})
        await send({"type": "http.response.body", "body": b'{"error":"Unauthorized: Missing or invalid API key"}'})
        return False
    return True


async def _send_json_resp(send, status: int, data: dict):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            (b"content-type", b"application/json; charset=utf-8"),
            (b"access-control-allow-origin", b"*"),
            (b"access-control-allow-methods", b"GET, POST, PATCH, DELETE, OPTIONS"),
            (b"access-control-allow-headers", b"Content-Type, Authorization, x-api-key"),
        ]
    })
    await send({"type": "http.response.body", "body": body})


async def _send_cors_preflight(send):
    await send({
        "type": "http.response.start",
        "status": 204,
        "headers": [
            (b"access-control-allow-origin", b"*"),
            (b"access-control-allow-methods", b"GET, POST, PATCH, DELETE, OPTIONS"),
            (b"access-control-allow-headers", b"Content-Type, Authorization, x-api-key"),
            (b"access-control-max-age", b"86400"),
        ]
    })
    await send({"type": "http.response.body", "body": b""})
