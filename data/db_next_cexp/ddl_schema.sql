-- db_next_cexp.dim_customer definition

CREATE TABLE db_next_cexp.dim_customer
(

    `customer_id` String,

    `group_customer_id` String,

    `customer_name_encrypted` String,

    `customer_age` Nullable(Int64),

    `customer_gender` Nullable(String),

    `customer_pronoun` Nullable(String),

    `customer_province_code` Nullable(String),

    `customer_province_name` Nullable(String),

    `customer_ward_code` Nullable(String),

    `customer_ward_name` Nullable(String),

    `customer_address` String,

    `customer_hometown` Nullable(String),

    `customer_career` Nullable(String),

    `_record_date` Date
)
ENGINE = ReplacingMergeTree
ORDER BY customer_id
SETTINGS index_granularity = 8192;


-- db_next_cexp.dim_customer_address_history definition

CREATE TABLE db_next_cexp.dim_customer_address_history
(

    `id` String,

    `customer_id` String,

    `address` String,

    `province_code` String,

    `province_name` String,

    `ward_code` String,

    `ward_name` String,

    `type` String,

    `status` UInt8,

    `_record_date` Date
)
ENGINE = ReplacingMergeTree
ORDER BY id
SETTINGS index_granularity = 8192;


-- db_next_cexp.dim_customer_contact definition

CREATE TABLE db_next_cexp.dim_customer_contact
(

    `contact_id` String,

    `customer_id` String,

    `type` String,

    `value_hashed` String,

    `value_encrypted` String,

    `is_primary` Nullable(UInt8),

    `is_verified` Nullable(UInt8),

    `created_timestamp` DateTime,

    `last_updated_timestamp` DateTime,

    `available_service` Array(String),

    `_record_date` Date
)
ENGINE = ReplacingMergeTree
ORDER BY contact_id
SETTINGS index_granularity = 8192;


-- db_next_cexp.dim_customer_event_group definition

CREATE TABLE db_next_cexp.dim_customer_event_group
(

    `id` String,

    `customer_id` String,

    `leader_id` String,

    `member_ids` Array(String),

    `event` String,

    `_record_date` Date
)
ENGINE = ReplacingMergeTree
ORDER BY customer_id
SETTINGS index_granularity = 8192;


-- db_next_cexp.dim_customer_group definition

CREATE TABLE db_next_cexp.dim_customer_group
(

    `group_customer_id` String,

    `primary_customer_name_encrypted` Nullable(String),

    `primary_customer_age` Nullable(String),

    `primary_customer_gender` Nullable(String),

    `primary_customer_pronoun` Nullable(String),

    `primary_customer_province_code` Nullable(String),

    `primary_customer_ward_code` Nullable(String),

    `primary_customer_hometown` Nullable(String),

    `primary_customer_career` Nullable(String),

    `_record_date` Date
)
ENGINE = ReplacingMergeTree
ORDER BY group_customer_id
SETTINGS index_granularity = 8192;


-- db_next_cexp.dim_product_vac definition

CREATE TABLE db_next_cexp.dim_product_vac
(

    `item_code` String,

    `product_name` String,

    `confirm_status` String,

    `is_active` UInt8,

    `universal_product_code` String,

    `product_industry_code` String,

    `product_industry_name` String,

    `product_group_code` String,

    `product_group_name` String,

    `is_hot_product` UInt8,

    `vat_output` Decimal(18,
 2),

    `vat_output_name` String,

    `vat_output_rate` Decimal(18,
 2),

    `vat_input` Decimal(18,
 2),

    `vat_input_name` String,

    `vat_input_rate` Decimal(18,
 2),

    `supplier_code` String,

    `supplier_name` String,

    `brand_name` String,

    `unit_code_level1` String,

    `unit_name_level1` String,

    `ratio_level1` Decimal(18,
 2),

    `unit_code_level2` String,

    `unit_name_level2` String,

    `ratio_level2` Decimal(18,
 2),

    `unit_code_level3` String,

    `unit_name_level3` String,

    `ratio_level3` Decimal(18,
 2),

    `is_combo` UInt8,

    `is_dose` UInt8,

    `reasonname_shop` String,

    `is_chronic_disease` UInt8,

    `vaccine_id` String,

    `vaccine_name` String,

    `disease_group_id` String,

    `disease_group_name` String,

    `_record_date` Date
)
ENGINE = ReplacingMergeTree
ORDER BY item_code
SETTINGS index_granularity = 8192;


-- db_next_cexp.dim_province definition

CREATE TABLE db_next_cexp.dim_province
(

    `province_code` String,

    `province_name` String,

    `province_english_name` Nullable(String),

    `province_level` String,

    `_record_date` Date
)
ENGINE = ReplacingMergeTree
ORDER BY province_code
SETTINGS index_granularity = 8192;


-- db_next_cexp.dim_regimen_vac definition

CREATE TABLE db_next_cexp.dim_regimen_vac
(

    `regimen_id` String,

    `vaccine_id` String,

    `age_unit` String,

    `from_age_number` Int64,

    `to_age_number` Int64,

    `schedule_type` String,

    `required_injections` Int64,

    `max_injections` Int64,

    `is_pregnant_regimen` UInt8,

    `_record_date` Date
)
ENGINE = ReplacingMergeTree
ORDER BY regimen_id
SETTINGS index_granularity = 8192;


-- db_next_cexp.dim_shop_vac definition

CREATE TABLE db_next_cexp.dim_shop_vac
(

    `shop_code` String,

    `shop_type` String,

    `shop_name` String,

    `shop_address` String,

    `shop_grand_opening_date` Date,

    `shop_opening_date` Date,

    `shop_closing_date` Date,

    `shop_province_name` String,

    `shop_province_code` String,

    `shop_area_name` String,

    `shop_region_name` String,

    `shop_ward_name` String,

    `shop_ward_code` String,

    `_record_date` Date
)
ENGINE = ReplacingMergeTree
ORDER BY shop_code
SETTINGS index_granularity = 8192;


-- db_next_cexp.dim_ward definition

CREATE TABLE db_next_cexp.dim_ward
(

    `ward_code` String,

    `ward_name` String,

    `ward_english_name` Nullable(String),

    `ward_level` String,

    `province_code` String,

    `province_name` String,

    `_record_date` Date
)
ENGINE = ReplacingMergeTree
ORDER BY (ward_code,
 province_code)
SETTINGS index_granularity = 8192;


-- db_next_cexp.fact_immunization_vac definition

CREATE TABLE db_next_cexp.fact_immunization_vac
(

    `indication_id` String,

    `attachment_code` String,

    `customer_id` String,

    `person_id` String,

    `lcv_id` String,

    `indication_note` String,

    `indication_status` String,

    `item_code` String,

    `product_item_code` String,

    `vaccine_name` String,

    `disease_name` String,

    `disease_group_id` String,

    `disease_group_name` String,

    `regimen_id` String,

    `regimen_name` String,

    `dose_number` Int64,

    `dosage` String,

    `unit_measure` String,

    `injection_route` String,

    `position` String,

    `lot_date` Date,

    `lot_number` String,

    `completed_ticket_date` Date,

    `ticket_status` String,

    `ticket_note` String,

    `conclusion` String,

    `injection_timestamp` DateTime,

    `completed_tracking_timestamp` DateTime,

    `is_leave_early` UInt8,

    `monitor_detail` String,

    `health_monitor_note` String,

    `shop_code` String,

    `shop_name` String,

    `is_returned` UInt8,

    `_record_date` Date
)
ENGINE = ReplacingMergeTree
ORDER BY indication_id
SETTINGS index_granularity = 8192;


-- db_next_cexp.fact_order_vac definition

CREATE TABLE db_next_cexp.fact_order_vac
(

    `order_detail_id` String,

    `attachment_code` String,

    `item_code` String,

    `customer_id` String,

    `lcv_id` String,

    `order_code` String,

    `order_status` String,

    `order_creation_date` Date,

    `order_completion_date` Date,

    `order_type` String,

    `package_type` String,

    `order_attribute` String,

    `order_channel` String,

    `payment_method` String,

    `shop_code` String,

    `shop_name` String,

    `item_name` String,

    `item_quantity` Int64,

    `item_price` Decimal(18,
 2),

    `item_servicefee` Decimal(18,
 2),

    `item_amount` Decimal(18,
 2),

    `item_servicefee_percent` Decimal(18,
 2),

    `item_discount_promotion` Decimal(18,
 2),

    `item_discount` Decimal(18,
 2),

    `item_amount_after_discount` Decimal(18,
 2),

    `item_unit_code` String,

    `item_unit_name` String,

    `item_discount_reason_code` String,

    `item_discount_reason_name` String,

    `is_partial_payment` UInt8,

    `order_injection` Int64,

    `_record_date` Date
)
ENGINE = ReplacingMergeTree
ORDER BY order_detail_id
SETTINGS index_granularity = 8192;


-- db_next_cexp.fact_return_order_vac definition

CREATE TABLE db_next_cexp.fact_return_order_vac
(

    `return_order_detail_id` String,

    `return_order_code` String,

    `attachment_code` String,

    `customer_id` String,

    `lcv_id` String,

    `item_code` String,

    `return_date` Date,

    `order_code` String,

    `order_status` String,

    `shop_code` String,

    `warehouse_code` String,

    `warehouse_name` String,

    `return_line_item_name` String,

    `return_line_item_quantity` Int64,

    `return_line_item_price` Decimal(18,
 2),

    `return_line_item_servicefee_percent` Decimal(18,
 2),

    `return_line_item_servicefee` Decimal(18,
 2),

    `return_line_item_amount` Decimal(18,
 2),

    `return_line_item_discount_promotion` Decimal(18,
 2),

    `return_line_item_discount` Decimal(18,
 2),

    `return_line_item_amount_after_discount` Decimal(18,
 2),

    `order_injection` Int64,

    `_record_date` Date
)
ENGINE = ReplacingMergeTree
ORDER BY return_order_detail_id
SETTINGS index_granularity = 8192;