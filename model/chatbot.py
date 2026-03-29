SYSTEM_PROMPT = """
You are a senior data analyst writing Spark SQL.

CRITICAL Spark SQL rules (must follow):
- NEVER use DISTINCT inside window functions (OVER).
- DO NOT write expressions like COUNT(DISTINCT col) OVER (...).
- If distinct counting is needed:
  - Use GROUP BY, or
  - Use a subquery / CTE to deduplicate first, then aggregate.

Aggregation rules:
- If SELECT contains aggregate functions,
  all non-aggregated columns MUST appear in GROUP BY.
- Prefer GROUP BY over window functions for counting users.

Join rules: 
- Please only join if needed
- Subqueries in WHERE clauses are NOT ALLOWED.
- Use JOINs to apply filters from other tables.

❌ Bad:
WHERE ctx_page_context = (SELECT item_code FROM item_metadata WHERE ten_sp LIKE '%iPhone%')

✅ Good:
JOIN item_metadata m
  ON e.ctx_page_context = m.item_code
WHERE m.ten_sp LIKE '%iPhone%'
"""

# Query guidelines:
# - Generate valid Spark SQL only.
# - Return SQL only. No explanation.
# - Do NOT use CTE (WITH) in SQLite
# - Use inline subqueries or direct aggregation instead

# Do not explain.
# Do not hallucinate columns.

def process_user_query(client, user_message):
    # This function rewrite the user query if it is ambigious and extract the entity in the rewritten query for finding the table schema 
    prompt = f"""You are a senior data analyst. 
    Your task is to rewrite the user's question to make it more clear and classify the user intention as generate_sql_query, explanation_sql_query, q_a.
    - If the user intention is generate_sql_query, rewrite the question to be more specific and clear for generating SQL query.
    - If the user intention are q_a or explanation_sql_query, rewrite the question to be more specific and clear.

    User question: {user_message}
    
    is_required_history: Based on the user question and the conversation history, determine whether the user question requires the context of the conversation history to be answered. If yes, set value = True, otherwise set value = False.
    entities: A list of business objects mentioned in the user query that corresponds to a dataset or table in the data warehouse.
    Examples: user, transaction, merchant, order, campaign.
    Entities help the system retrieve the correct tables before generating SQL.

    Output JSON schema:

    {{
        "user_intention": string (generate_sql_query, explanation_sql_query, q_a),
        "rewritten_query": string (Vietnamese query),
        "entities": string[],
        "is_required_history": boolean
    }}
    Never invent fields or metrics that are not explicitly or implicitly mentioned."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content

def text_to_structure(client, question):
    prompt = f"""
    You are a semantic parser for database analytics questions.

    Your task is to extract the semantic elements of the user's question.
    Do NOT generate SQL.
    Do NOT explain your reasoning.
    Only return valid JSON following the schema below.

    Semantic elements to extract:
    1. Require explanation: 
    Based on the query then choose whether the user require explaination or not. 
    2. Services: 
    Choose which Service Data is [Vaccine, FSHOP], only choose 1 service for one user query. 

    3. intention:
    Choose ONLY one of the following values:
    - aggregate:
        + sum: Tổng số, tổng 
        + count: Số lượng, số 
        + avg: Trung bình 
        + min: nhỏ nhất 
        + max: nhỏ nhất 
    - trend          (metric over time)
    - ranking        (top / bottom)
    - filter         (subset without aggregation)
    - comparison     (compare two or more groups)
    - detail         (raw records)

    4. metric:
    - What is being measured: 
        + identified user: Khách hàng định danh
        + anonymous users: Khách hàng ẩn danh 
        + event, url
        + screen location: vị trí màn hình 
    - If unclear, set value = null

    5. time:
    - When does the question refer to?
    - Include time range and time granularity if mentioned
    - If not mentioned, set value = null

    6. dimension:
    - A dimension is a field used to GROUP the results in an aggregated query.
    - Dimensions determine how the metric is broken down into groups.
    - Dimensions appear in the GROUP BY clause in SQL.
    - Do NOT include fields that are only used for filtering.
    - Time granularity (day, week, month) is also a dimension when grouping over time.

    Examples:
    - "Doanh thu theo ngày" → dimension = ["day"]
    - "User theo platform" → dimension = ["platform"]
    - "Top 10 sản phẩm" → dimension = ["product"]
    - "Doanh thu theo ngày theo platform" → dimension = ["day", "platform"]

    7. filter:
    - Conditions applied to the data
    - Return an array of objects with (field, operator, value)
    - If none, return empty array []

    8. event_context:
    Represents the contextual information about user behavior.
    It may contain:
        - screen_description: the screen / page where the action happens
        - action_description: the action performed by the user
    Rules:
    - Either field may be null.
    - Both fields may be null.
    - If only screen is mentioned → action_description = null.
    - If only action is mentioned → screen_description = null.
    - Do NOT merge them into one sentence.
    - Keep them separate and concise.

    Examples: 
    - "Số lượng khách hàng xem trang chi tiết sản phẩm ngày 16/08/2025" -> 
    {{
        "screen_description": "màn hình chi tiết sản phẩm",
        "action_description": "xem trang"
    }}
    - "Số lượng khách hàng click vào đơn hàng của tôi" ->
    {{
        "screen_description": null,
        "action_description": "click vào đơn hàng của tôi"
    }}
    - If unclear, set value = null

    Output JSON schema:

    {{
        "is_required_explanation": "True" | "False",
        "service":string,
        "intention": string,
        "metric": string | null,
        "time": {{
            "range": string | null,
            "grain": string | null
        }} | null,
        "dimension": string[],
        "filter": {{
            "field": string,
            "operator": string,
            "value": string
        }}[],
        "event_context": {{
            "screen_description": string | null,
            "action_description": string | null
        }} | null

    }}

    If the user question is ambiguous, make the best reasonable assumption.
    Never invent fields or metrics that are not explicitly or implicitly mentioned.

    User question:
    {question}

    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content

def text_to_sql(client,question,knowledge,structure,table_schema, is_explanation, history=None, dialect="SQL"):
    prompt = f"""
    SQL Dialect: {dialect}

    Schema:
    {table_schema}

    Question:
    {question}

    Business Rules:
    {knowledge}

    Structure:
    {structure}

    Conversation History: 
    {history}

    If user ask number of view, please use select (*) as view_count as default. 
    If user ask another question, please using the knowledges above. 
    Only use the tables and columns in the Schema to generate SQL query, do not hallucinate any table or column that is not in the Schema.
    Based on the Schema, Question, Business Rules and Structure 

    """
    if is_explanation:
        prompt +=f"""
        Return each step and explanation that come up the result, then the final result is SQL query.
        All the explanation and step will be written in Vietnamese. 
        """
    else:
        prompt +="""Return only SQL query, do not explain."""
    print(prompt)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content

def text_to_explore(client,question,knowledge,structure,table_schema, history=None):
    prompt = f"""
    Finding related schema table:
    {table_schema}

    Question:
    {question}

    Business Rules:
    {knowledge}

    Structure:
    {structure}

    Conversation History: 
    {history}

    Only based on the tables and columns in the Schema, do not hallucinate any table or column that is not in the Schema.
    Based on the Schema, Question, Business Rules, Structure, Conversation History
    Return the previous user question if they require to lookback. 
    Return the answer for user question to explore the data or Q/A, the answer in Vietnamese. 

    Output:
        Only output the Vietnamese answer.        
    """
    print(prompt)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content


def recommend_next_action(client, question, sql_query, schema, error_message=None):
    print(sql_query, error_message)
    if error_message is None:
        prompt = f"""
        You are a advisor after reviewing the SQL query.
        The SQL query is valid. Based on the user's question, suggest additional approaches or insights the user can explore.

        Rules:
        - Only provide suggestions that are relevant to the user's question
        - Use the user's question and the SQL query to provide meaningful suggestions.
        - Do NOT invent columns or tables that are not in the schema.
        - Suggestions should be actionable and relevant to the user's question.
        - Suggest the next steps for user can explore the data.
        - Do NOT provide any SQL code. 

        User Question:
        {question}

        Output:
        Provide 2-3 actionable suggestions in Vietnamese.
        """
        print("recommend prompt:", prompt)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
            {"role": "system", "content": prompt}
        ],
            temperature=0
        )
    else: 
        prompt = f"""
        You are a SQL validator and error explainer.

        Your task is to analyze the given SQL query, identify why it is invalid, and provide a clear explanation to the user.
        Use the provided database schema to validate the query.

        Rules:
        - Do NOT invent columns or tables that are not in the schema.
        - If the query references a non-existent table or column, explain which table or column is invalid.
        - If the query has a syntax error, explain the issue clearly.
        - If the query violates any database constraints, explain the violation.
        - Provide suggestions to fix the query if possible.

        Database Schema:
        {schema}

        User Question:
        {question}

        SQL Query:
        {sql_query}

        Error Message:
        {error_message}

        Output:
        Only output the fixed SQL query.        
        """
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

    return response.choices[0].message.content