#!/usr/bin/env python3
import json, sys
thread = "thr_fake"
turn = "turn_fake"
thread_name = None
thread_goal = None
metadata = {"isPinned": False, "gitInfo": {}}
has_dynamic_tools = False
pending_dynamic = False
for line in sys.stdin:
    m = json.loads(line)
    method = m.get("method")
    rid = m.get("id")
    if rid == 900 and method is None:
        result = m.get("result") or {}
        ok = bool(result.get("success"))
        text = ((result.get("contentItems") or [{}])[0].get("text") or "") if isinstance(result, dict) else ""
        print(json.dumps({"method":"item/completed","params":{"threadId":thread,"turnId":turn,"item":{"id":"dyn1","type":"dynamicToolCall","tool":"status","arguments":{},"status":"completed" if ok else "failed","contentItems":result.get("contentItems") or [],"success":ok}}}), flush=True)
        print(json.dumps({"method":"item/agentMessage/delta","params":{"threadId":thread,"turnId":turn,"itemId":"i1","delta":"dynamic:"+text[:120]}}), flush=True)
        print(json.dumps({"method":"turn/completed","params":{"threadId":thread,"turn":{"id":turn,"status":"completed"}}}), flush=True)
        continue
    if rid is None:
        continue
    if method == "initialize":
        # Real app-server may emit notifications before initialize completes.
        print(json.dumps({"method":"account/updated","params":{"account":None}}), flush=True)
        print(json.dumps({"id":rid,"result":{"userAgent":"fake"}}), flush=True)
    elif method == "configRequirements/read":
        print(json.dumps({"id":rid,"result":{"requirements":{"allowedApprovalPolicies":["never","onRequest"],"allowedSandboxModes":["workspace-write","read-only","readOnly"]}}}), flush=True)
    elif method == "thread/start":
        params=m.get("params",{})
        has_dynamic_tools=bool(params.get("dynamicTools"))
        expected="read-only" if has_dynamic_tools else "workspace-write"
        if params.get("sandbox") != expected:
            print(json.dumps({"id":rid,"error":{"code":-32602,"message":"bad sandbox mode"}}), flush=True)
        else:
            print(json.dumps({"id":rid,"result":{"thread":{"id":thread}}}), flush=True)
    elif method == "thread/resume":
        print(json.dumps({"id":rid,"result":{"thread":{"id":thread,"name":thread_name}}}), flush=True)
    elif method == "turn/start":
        policy=m.get("params",{}).get("sandboxPolicy",{}).get("type")
        expected_policy="readOnly" if has_dynamic_tools else "workspaceWrite"
        if policy != expected_policy:
            print(json.dumps({"id":rid,"error":{"code":-32602,"message":"bad sandbox policy"}}), flush=True)
            continue
        print(json.dumps({"id":rid,"result":{"turn":{"id":turn,"status":"inProgress","items":[]}}}), flush=True)
        print(json.dumps({"method":"turn/started","params":{"threadId":thread,"turn":{"id":turn,"status":"inProgress"}}}), flush=True)
        if has_dynamic_tools:
            print(json.dumps({"method":"item/started","params":{"threadId":thread,"turnId":turn,"item":{"id":"dyn1","type":"dynamicToolCall","namespace":"reasonfirst_remote","tool":"status","arguments":{},"status":"inProgress"}}}), flush=True)
            print(json.dumps({"id":900,"method":"item/tool/call","params":{"threadId":thread,"turnId":turn,"callId":"dyn1","namespace":"reasonfirst_remote","tool":"status","arguments":{}}}), flush=True)
