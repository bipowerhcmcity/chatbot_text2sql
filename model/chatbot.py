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
- If user request the information of item, join the cdp_events.ctx_page_context==item_metadata.item_code
- Please only join if needed
- Subqueries in WHERE clauses are NOT ALLOWED.
- Use JOINs to apply filters from other tables.

❌ Bad:
WHERE ctx_page_context = (SELECT item_code FROM item_metadata WHERE ten_sp LIKE '%iPhone%')

✅ Good:
JOIN item_metadata m
  ON e.ctx_page_context = m.item_code
WHERE m.ten_sp LIKE '%iPhone%'

User identity rules:
- cdp_id = universal user identifier, always present for all users.
- user_id = identified user identifier (logged-in users).
- An anonymous user is defined as a user who has a cdp_id but does not have a user_id (user_id IS NULL or blank)
- An identified user is defined as a user who has both a cdp_id and a user_id (user_id IS NOT NULL or not blank)
- Users must never be counted by user_id, unless the question explicitly requests it.
- Do NOT mix cdp_id and user_id unless explicitly requested.

Query guidelines:
- Generate valid Spark SQL only.
- Return SQL only. No explanation.
- Do NOT use CTE (WITH) in SQLite
- Use inline subqueries or direct aggregation instead

Do not explain.
Do not hallucinate columns.
"""

TABLE_SCHEMA = """
Table: cdp_events 
* -- Each row illustrate the event of user in website. For example, if you count number of event, you can use select count(*) as view_count
cdp_id -- anoynymous user id VARCHAR,

user_id -- identified user id VARCHAR,
user_time TIMESTAMP,  -- user interaction time, in format YYYY-mm-dd hh:mm:ss.mmmm. eg: 2025-08-25 20:15:30.572
date DATE, -- user interaction date, in format YYYY-mm-dd. eg: 2025-08-25. Data start from 2025 

platform VARCHAR,
referrer_url TEXT,
url TEXT,

ctx_userId UUID,
ctx_eventIndex INT,
ctx_event_name VARCHAR,
ctx_screen_location VARCHAR,
ctx_location_type VARCHAR,
ctx_location_name VARCHAR,

ctx_firstEventId UUID,
ctx_firstEventTimestamp TIMESTAMP,

ctx_sessionId UUID, -- Phiên truy cập, lượt truy cập
ctx_sessionIndex INT,
ctx_previousSessionId UUID,

ctx_page_context VARCHAR, -- This is an itemcode of the item that people is view in eg: 00003278

ctx_order_id VARCHAR,
ctx_order_type VARCHAR,
ctx_payment_type VARCHAR,

ctx_shipping_fee NUMERIC,
ctx_discounted_value NUMERIC,

ctx_fpt_uuid UUID,

device_brand VARCHAR,
device_model VARCHAR,
device_os VARCHAR,
device_os_version VARCHAR,
device_browser VARCHAR,
viewport_size VARCHAR,

ctx_osVersion VARCHAR,
ctx_osType VARCHAR,
ctx_deviceModel VARCHAR,
ctx_deviceManufacturer VARCHAR,

Table: item_metadata

item_code VARCHAR PRIMARY KEY, eg: 00003278

ten_sp VARCHAR,             -- product name. eg: Điện thoại iPhone 6 64GB Xám MG4F2VN/A
ten_viet_tat VARCHAR,       -- short Vietnamese name eg: iPhone 6 64GB
ten_upc VARCHAR,            -- UPC eg: iPhone 6
ten_nhom VARCHAR,           -- product group eg: Apple iPhone 6-128G
ten_dong VARCHAR,           -- product line eg: iPhone 6
ten_model VARCHAR,          -- model eg: iPhone 6-64
ten_nhan VARCHAR,           -- brand eg: Apple
ten_nganh VARCHAR,          -- industry eg: Apple
ten_loai VARCHAR,           -- category eg: ĐTDĐ-Apple
mau_sac VARCHAR,            -- color eg: ['Xám']

ten_don_vi_tinh VARCHAR      -- unit name: Chiếc

You are generating SQL queries for an order detail table.

Table: order_detail

Grain:
- Each row represents ONE order line (one product in one order).
- order_detail_id uniquely identifies a row.
- order_id can appear multiple times.
- item_code identifies the product in the order line.

COLUMN SEMANTICS:

Order identification:
- order_detail_id: unique identifier of an order line.
- order_id: identifier of the order (NOT unique per row).
- order_code: business order code.

Product information:
- item_code: product identifier.
- item_name: product name at order time.
- barcode: product barcode.
- unit_code, unit_name: unit of measurement.

Quantity & pricing (LINE-LEVEL):
- quantity: number of items sold in this order line.
- _group_price: unit price before discount.
- _group_total: total line amount before tax.
- _group_tprice_after_discount: total line amount after discount.
- _group_discount: discount amount at line level.
- _group_discount_promotion: promotion discount amount.
- _group_total_tax: tax amount for the order line.
- tax_rate: tax rate applied to the order line.

Promotion & flags:
- is_promotion: whether the order line is promotional.
- is_hot: whether the item is marked as hot.
- discount_type: type of discount applied.

Warehouse & fulfillment:
- whs_code, whs_name: warehouse information.
- is_inventory_management: inventory management flag.
- is_serial, is_expired_date: product control flags.

Order-line attributes:
- line_code, line_num
- order_detail_attribute
- meta_data

TIME & PARTITION:
- date (yyyy-MM-dd) represents the business date of the order line.

AGGREGATION RULES:
- This table is at ORDER-LINE level.
- Do NOT treat one row as one order.
- When counting orders, ALWAYS use COUNT(DISTINCT order_id).
- When calculating revenue per product:
  → SUM(_group_tprice_after_discount) or SUM(_group_total).
- When calculating quantity sold:
  → SUM(quantity).
- Do NOT sum order-level fields in this table.

FILTERING RULES:
- Product filtering should use item_code or item_name.
- Treat item_name as non-unique by default.
- Use LIKE for product name matching.
- Time-based filtering should use the date column.

SUBQUERY & JOIN RULES:
- Avoid scalar subqueries.
- If product metadata is required, JOIN with item_metadata on item_code.
- Prefer JOIN over subqueries when enriching product information.

COMMON MISTAKES TO AVOID:
- COUNT(order_id) without DISTINCT.
- SUM order-level values that are repeated per order.
- Mixing order-level and order-line-level metrics.
- Assuming item_name uniquely identifies a product.

OUTPUT REQUIREMENTS:
- Generate syntactically correct SQL.
- Ensure business logic correctness over SQL brevity.

"""

def text_to_structure(client, question):
    prompt = f"""
    You are a semantic parser for database analytics questions.

    Your task is to extract the semantic elements of the user's question.
    Do NOT generate SQL.
    Do NOT explain your reasoning.
    Only return valid JSON following the schema below.

    Semantic elements to extract:

    1. intention:
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

    2. metric:
    - What is being measured: 
        + identified user: Khách hàng định danh
        + anonymous users: Khách hàng ẩn danh 
        + event, url
        + screen location: vị trí màn hình 
    - If unclear, set value = null

    3. time:
    - When does the question refer to?
    - Include time range and time granularity if mentioned
    - If not mentioned, set value = null

    4. dimension:
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

    5. filter:
    - Conditions applied to the data
    - Return an array of objects with (field, operator, value)
    - If none, return empty array []

    6. event_context:
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

def text_to_sql(client,question,knowledge,structure, dialect="SQL"):
    prompt = f"""
    SQL Dialect: {dialect}

    Schema:
    {TABLE_SCHEMA}

    Question:
    {question}

    Knowledge:
    {knowledge}

    Structure:
    {structure}

    If user only ask to view the product, please fitler ctx_screen_location = "product_detail", ctx_event_name = "view_page". 
    If user ask number of view, please use select (*) as view_count as default. 
    If user ask another question, please using the knowledges above. 
    Based on the Schema, Question, Knowledge and Structure -> Return only SQL.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content
