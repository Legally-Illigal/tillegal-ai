# Source-level execution trace chi tiết

Authority [agent.py29–95](../../../src/applications/tillegal/agents/query/agent.py). Signature OBSERVED `(question: str) -> dict`. Đây là hàm nghiệp vụ duy nhất trong Query module;không có project helper normalize/analyze/plan riêng. Subquery15–17,QueryPlan20–26 và QueryInputError11–12 là classes,schema/error behavior kế thừa Pydantic/ValueError.

## Dòng31–32

```python
    if not isinstance(question, str):
        raise QueryInputError("QUERY_INPUT_TYPE")
```

- READ: question raw object.
- ACTION / CREATED: Không tạo text/model nếu không str.
- NEXT / OUTPUT: TYPE guard; đi33 hoặc raise QUERY_INPUT_TYPE.

## Dòng33–34

```python
    if not 1 <= len(question) <= 10000:
        raise QueryInputError("QUERY_INPUT_LENGTH")
```

- READ: question và len(question).
- ACTION / CREATED: Không mutate raw input.
- NEXT / OUTPUT: LENGTH guard trước normalize; đi35 hoặc raise.

## Dòng35–36

```python
    if any(unicodedata.category(char) in {"Cc", "Cs"} and char not in "\t\n\r" for char in question):
        raise QueryInputError("QUERY_INPUT_CHARACTER")
```

- READ: char trong raw question.
- ACTION / CREATED: any short-circuit trên Cc/Cs với tab/LF/CR exception.
- NEXT / OUTPUT: Đi37 hoặc CHARACTER error;không phải replace/delete control.

## Dòng37–39

```python
    text = unicodedata.normalize("NFC", question).strip()
    if not text:
        raise QueryInputError("QUERY_INPUT_EMPTY")
```

- READ: question raw đã qua3 guards.
- ACTION / CREATED: text=NFC+strip;question không bị gán lại.
- NEXT / OUTPUT: text rỗng→EMPTY;khác→parts.

## Dòng40–44

```python
    parts = [
        s.strip(" ?;")
        for s in re.split(r"[;?\n]+|\s+và\s+(?=(?:khi nào|ai |bao nhiêu|điều kiện|thủ tục))", text, flags=re.I)
        if s.strip(" ?;")
    ]
```

- READ: text.
- ACTION / CREATED: parts từ split/strip/filter;comprehension variable s không public.
- NEXT / OUTPUT: List parts có thể rỗng hoặc còn tab-only part.

## Dòng45–48

```python
    prefix = re.match(r"^(?:trích dẫn|trích nguyên văn|tìm đoạn)\s*[:\s]\s*", text, re.I)
    topic = text[prefix.end() :].strip(' “”?."') if prefix else ""
    quote_only = bool(topic and len(parts) == 1)
    queries = [topic] if quote_only else parts[:4] or [text]
```

- READ: text và parts.
- ACTION / CREATED: prefix Match/None;topic str;quote_only bool;queries list.
- NEXT / OUTPUT: Lookup1 topic hoặc parts[:4]/fallback[text].

## Dòng49–62

```python
    dates = []
    invalid_date = False
    for match in re.finditer(
        r"(?<![/\w])(?:\d{1,2}/\d{1,2}/\d{4}|(?:19|20)\d{2}|hiện nay|hiện hành)(?![/\w])", text, re.I
    ):
        mention = match.group()
        if "/" in mention:
            day, month, year = map(int, mention.split("/"))
            try:
                date(year, month, day)
            except ValueError:
                invalid_date = True
                continue
        dates.append(mention)
```

- READ: text và raw temporal matches.
- ACTION / CREATED: dates list[str],invalid_date bool,mention/day/month/year locals.
- NEXT / OUTPUT: date ValueError chỉ bật flag rồi continue;mentions hợp lệ append.

## Dòng63–71

```python
    clarification = None
    if len(parts) > 4:
        clarification = "Vui lòng chia câu hỏi thành tối đa bốn phần."
    elif (
        (not topic and prefix)
        or len(text.split()) < 2
        or text.casefold().strip(" ?") in {"có được không", "như vậy đúng không", "trường hợp này"}
    ):
        clarification = "Bạn cần tra cứu quy định hoặc tình huống cụ thể nào?"
```

- READ: parts,prefix,topic,text.
- ACTION / CREATED: clarification None hoặc literal message.
- NEXT / OUTPUT: Too-many thắng generic do if/elif;chưa quyết định graph ở hàm này.

## Dòng72–73

```python
    if invalid_date:
        clarification = "Ngày được nêu không hợp lệ. Bạn vui lòng kiểm tra lại ngày, tháng và năm."
```

- READ: invalid_date và clarification hiện có.
- ACTION / CREATED: Ghi đè clarification nếu có ngày sai.
- NEXT / OUTPUT: Message ngày sai có priority cuối.

## Dòng74–74

```python
    subqueries = [Subquery(text=q, purpose="lookup" if quote_only else "question_part") for q in queries]
```

- READ: queries,quote_only.
- ACTION / CREATED: list Subquery models;purpose lookup/question_part.
- NEXT / OUTPUT: ValidationError có thể propagate nếu text không qua schema.

## Dòng75–87

```python
    if not quote_only:
        topics = re.finditer(
            r"đối thoại định kỳ|nghỉ hằng năm|nghỉ phép|thời giờ làm việc|"
            r"chấm dứt hợp đồng lao động|tiền lương|làm thêm giờ",
            text,
            re.I,
        )
        seen = {q.casefold() for q in queries}
        for match in topics:
            topic_text = match.group()
            if len(subqueries) < 4 and topic_text.casefold() not in seen:
                subqueries.append(Subquery(text=topic_text, purpose="topic"))
                seen.add(topic_text.casefold())
```

- READ: text,subqueries,queries.
- ACTION / CREATED: topics iterator,seen set,topic_text;append bounded extras.
- NEXT / OUTPUT: Skip nếu lookup;topic duplicate/full-cap không append.

## Dòng88–95

```python
    return QueryPlan(
        original=question,
        intent="quote_lookup" if quote_only else "legal_question",
        domain="labour" if re.search(r"lao động|tiền lương|nghỉ phép|làm việc", text, re.I) else "unknown",
        temporal_scope=dates,
        clarification=clarification,
        subqueries=subqueries,
    ).model_dump()
```

- READ: question,quote_only,text,dates,clarification,subqueries.
- ACTION / CREATED: QueryPlan object tạm,domain regex chạy ngay tại constructor.
- NEXT / OUTPUT: model_dump trả dict;không có named plan local trong understand.

## Call-return dossiers

### Standalone understand

FROM: application caller hoặc test.

CALL: src/applications/tillegal/agents/query/agent.py:understand(question: str),29–95.

INPUT: raw question object;annotation str không thay guards31–39.

ACTION: Các blocks ở trên,không I/O hoặc model inference.

RETURN: dict sáu keys từ QueryPlan(...).model_dump(),hoặc QueryInputError/Pydantic exception.

BACK TO: caller standalone;hoặc QuerySearch.search20–21 chuyển dict vào Search;hoặc QuerySearchNodes.query25 giữ dict trong graph update.

### Subquery schema

FROM: understand74 và86.

CALL: Subquery(text=q,purpose=...),class15–17.

INPUT: text string từ queries hoặc regex group,purpose literal.

ACTION: Pydantic validate length1–10000/literal. Không whitespace-only validator riêng.

RETURN: Subquery instance;ValidationError nếu schema fail.

BACK TO: list subqueries trong understand;không có ML embedding.

### QueryPlan schema và dict serialization

FROM: understand88–95.

CALL: QueryPlan(original=question,...),class20–26;rồi inherited model_dump() không arguments.

INPUT: sáu field values được xây trước đó;domain được tính inline91.

ACTION: Pydantic shape/literal/cardinality constraints;không calendar parser trong model.

RETURN: model tạm rồi Python dict,nested Subquery thành dicts,clarification None vẫn xuất hiện.

BACK TO: understand return ngay;không normalized_text public field hoặc instance được lưu global.

### QuerySearch orchestration

FROM: caller `await pipeline.search(question)`.

CALL: QuerySearch.search(self,question:str)->SearchState,src/query_search_bootstrap.py20–21.

INPUT: question và self.retrieval/self.options đã inject.

ACTION: call understand rồi await Search Agent search(plan,retrieval,options).

RETURN: SearchState hoặc exception;clarification guard thuộc receiving Search.

BACK TO: caller không dùng LangGraph ở đường này.

### Graph query node

FROM: GraphExecutor → compiled graph START→query.

CALL: QuerySearchNodes.query(self,state:LegalQAState)->LegalQAState,graphs/legal_qa.py24–33.

INPUT: state.question;pipeline.options là dependency tin cậy.

ACTION: understand đúng1 lần;local plan ở node là returned dict;gán options/clarification/status,reset downstream fields None.

RETURN: partial update dict;exception không catch để giữ typed behavior.

BACK TO: LangGraph merge channel rồi route_query36–37 đọc clarification.

### Route và receiving boundary

FROM: LangGraph scheduler sau query update.

CALL: route_query(state)->Literal[search,end],36–37.

INPUT: state.clarification do node tạo.

ACTION: truthy→end,otherwise→search. Không legal Judge decision.

RETURN: label;missing key ở raw call gây KeyError (observed boundary probe).

BACK TO: END hoặc Search node39–54 gọi Search Agent38–56. Search model_validate plan/options,guard clarification,prebuild requests từ parsed.subqueries.text;chi tiết contract ở10.

Tất cả ranges trên được AST kiểm trong16/evidence/source-symbols.json. Inherited Pydantic model_validate/model_dump không có project implementation lines riêng;không bịa helper function hoặc gán code thư viện thành source dự án.
