/* ======================================================
   LONG CHÂU – VACCINE
   ====================================================== */

-- =========================
-- DIMENSION TABLES
-- =========================

CREATE TABLE dim_shop (
    code VARCHAR(50) PRIMARY KEY,
    shop_type VARCHAR(50),
    region_insurance VARCHAR(50),
    legal_entity VARCHAR(50),
    regulated_ward VARCHAR(50),
    regulated_province VARCHAR(50),
    district VARCHAR(50),
    ward VARCHAR(50),
    region VARCHAR(50),
    area VARCHAR(50),
    province VARCHAR(50),
    name VARCHAR(255),
    status BOOLEAN,
    address VARCHAR(255),
    shop_scope VARCHAR(50),
    short_name VARCHAR(100),
    name_on_bill VARCHAR(255),
    shop_code_hub VARCHAR(50),
    ware_house_ho VARCHAR(50),
    province_name VARCHAR(100),
    area_name VARCHAR(100),
    region_name VARCHAR(100),
    ward_name VARCHAR(100),
    district_name VARCHAR(100),
    longitude DECIMAL(10,6),
    latitude DECIMAL(10,6),
    grand_opening_date DATE,
    opening_date DATE,
    closing_date DATE,
    legal_entity_name VARCHAR(255),
    tax_code VARCHAR(50),
    shop_type_name VARCHAR(100),
    etl_date TIMESTAMP,
    tenant VARCHAR(50)
);

CREATE TABLE dim_satellite_shop (
    id VARCHAR(36) PRIMARY KEY,
    shop_code_vaccine VARCHAR(50),
    shop_name_vaccine VARCHAR(255),
    shop_code_longchau VARCHAR(50),
    shop_name_longchau VARCHAR(255),
    shop_type VARCHAR(50),
    status BOOLEAN,
    effective_from_date DATE,
    effective_to_date DATE,
    is_deleted BOOLEAN,
    etl_date TIMESTAMP,
    etl_by VARCHAR(50),
    primary_checksum VARCHAR(64),
    record_checksum VARCHAR(64)
);

CREATE TABLE dim_product (
    product_id VARCHAR(50),
    product_unit_id VARCHAR(50),
    product_name VARCHAR(255),
    item_code VARCHAR(50),
    universal_product_code VARCHAR(50),
    product_group_code VARCHAR(50),
    product_group_name VARCHAR(100),
    product_industry_code VARCHAR(50),
    product_industry_name VARCHAR(100),
    brand_name VARCHAR(100),
    supplier_code VARCHAR(50),
    supplier_name VARCHAR(255),
    vat_output_rate DECIMAL(5,2),
    vat_input_rate DECIMAL(5,2),
    is_active BOOLEAN,
    is_combo BOOLEAN,
    is_dose BOOLEAN,
    is_chronic_disease BOOLEAN,
    created_date DATE,
    updated_date DATE,
    etl_date TIMESTAMP,
    PRIMARY KEY (product_id, product_unit_id)
);

CREATE TABLE dim_vaccine_regimen (
    regimen_detail_id VARCHAR(36) PRIMARY KEY,
    regimen_id VARCHAR(36),
    vaccine_id VARCHAR(50),
    from_age_number INT,
    to_age_number INT,
    age_unit VARCHAR(20),
    schedule_type VARCHAR(255),
    required_injections INT,
    max_injections INT,
    dosage VARCHAR(50),
    unit VARCHAR(20),
    nearest_injection_distance INT,
    min_distance INT,
    max_distance INT,
    is_pregnant_regimen BOOLEAN,
    is_required BOOLEAN,
    note TEXT,
    created_at TIMESTAMP,
    modified_at TIMESTAMP,
    etl_date TIMESTAMP,
    etl_by VARCHAR(50),
    primary_checksum VARCHAR(64),
    record_checksum VARCHAR(64)
);

CREATE TABLE dim_vaccine_disease_group (
    id VARCHAR(36) PRIMARY KEY,
    item_code VARCHAR(50),
    vaccine_id VARCHAR(50),
    vaccine_name VARCHAR(255),
    disease_group_id VARCHAR(50),
    disease_group_name VARCHAR(255),
    note TEXT,
    start_date DATE,
    end_date DATE,
    current_flag CHAR(1),
    etl_date TIMESTAMP,
    etl_by VARCHAR(50),
    primary_checksum VARCHAR(64),
    record_checksum VARCHAR(64)
);

CREATE TABLE dim_person (
    id VARCHAR(36) PRIMARY KEY,
    lcv_id VARCHAR(50),
    person_id VARCHAR(50),
    customer_id VARCHAR(50),
    person_name VARCHAR(255),
    gender VARCHAR(20),
    identity_card VARCHAR(50),
    date_of_birth DATE,
    phone_number VARCHAR(20),
    email VARCHAR(100),
    nationality_code VARCHAR(20),
    ethnic_code VARCHAR(20),
    is_test BOOLEAN,
    start_date DATE,
    end_date DATE,
    current_flag CHAR(1),
    etl_date TIMESTAMP,
    etl_by VARCHAR(50),
    primary_checksum VARCHAR(64),
    record_checksum VARCHAR(64)
);

CREATE TABLE dim_person_address (
    id VARCHAR(36) PRIMARY KEY,
    lcv_id VARCHAR(50),
    province_code VARCHAR(20),
    province_name VARCHAR(100),
    district_code VARCHAR(20),
    district_name VARCHAR(100),
    ward_code VARCHAR(20),
    ward_name VARCHAR(100),
    address VARCHAR(255),
    type VARCHAR(20),
    status BOOLEAN,
    is_new BOOLEAN,
    creation_time TIMESTAMP,
    modified_time TIMESTAMP,
    etl_date TIMESTAMP,
    primary_checksum VARCHAR(64),
    record_checksum VARCHAR(64)
);

CREATE TABLE dim_family_member (
    lcv_id VARCHAR(50),
    person_id VARCHAR(50),
    person_name VARCHAR(255),
    family_profile_id VARCHAR(50),
    family_name VARCHAR(255),
    family_person_title VARCHAR(50),
    is_guardian BOOLEAN,
    start_date DATE,
    end_date DATE,
    current_flag CHAR(1),
    is_deleted BOOLEAN,
    etl_date TIMESTAMP,
    etl_by VARCHAR(50),
    primary_checksum VARCHAR(64),
    record_checksum VARCHAR(64)
);

-- =========================
-- FACT TABLES
-- =========================

CREATE TABLE fact_vaccine_sales_order_detail (
    order_detail_id VARCHAR(50) PRIMARY KEY,
    order_code VARCHAR(50),
    attachment_code VARCHAR(50),
    item_code VARCHAR(50),
    item_name VARCHAR(255),
    item_quantity INT,
    item_price DECIMAL(18,2),
    item_amount DECIMAL(18,2),
    item_discount DECIMAL(18,2),
    item_amount_after_discount DECIMAL(18,2),
    order_status VARCHAR(50),
    order_creation_date TIMESTAMP,
    order_completion_date TIMESTAMP,
    customer_id VARCHAR(50),
    lcv_id VARCHAR(50),
    shop_code VARCHAR(50),
    warehouse_code VARCHAR(50),
    order_channel VARCHAR(50),
    payment_method VARCHAR(50),
    is_partial_payment BOOLEAN,
    etl_date TIMESTAMP,
    etl_by VARCHAR(50),
    primary_checksum VARCHAR(64),
    record_checksum VARCHAR(64)
);

CREATE TABLE fact_vaccine_returned_order_detail (
    return_order_detail_id VARCHAR(50) PRIMARY KEY,
    return_order_code VARCHAR(50),
    order_code VARCHAR(50),
    attachment_code VARCHAR(50),
    item_code VARCHAR(50),
    return_line_item_name VARCHAR(255),
    return_line_item_quantity INT,
    return_line_item_price DECIMAL(18,2),
    return_line_item_amount DECIMAL(18,2),
    return_date TIMESTAMP,
    shop_code VARCHAR(50),
    warehouse_code VARCHAR(50),
    is_partial_payment BOOLEAN,
    etl_date TIMESTAMP,
    etl_by VARCHAR(50),
    primary_checksum VARCHAR(64),
    record_checksum VARCHAR(64)
);

CREATE TABLE fact_vaccine_record (
    attachment_code VARCHAR(50) PRIMARY KEY,
    lcv_id VARCHAR(50),
    person_id VARCHAR(50),
    person_name VARCHAR(255),
    gender VARCHAR(20),
    vaccine_id VARCHAR(50),
    vaccine_name VARCHAR(255),
    disease_group_id VARCHAR(50),
    regimen_id VARCHAR(50),
    dose_number INT,
    dosage VARCHAR(50),
    unit_measure VARCHAR(20),
    injection_route VARCHAR(50),
    lot_number VARCHAR(50),
    lot_date DATE,
    injection_time TIMESTAMP,
    conclusion VARCHAR(255),
    shop_code VARCHAR(50),
    doctor_code VARCHAR(50),
    injection_nursing_code VARCHAR(50),
    is_returned BOOLEAN,
    is_test BOOLEAN,
    etl_date TIMESTAMP,
    etl_by VARCHAR(50),
    primary_checksum VARCHAR(64),
    record_checksum VARCHAR(64)
);

/* ============================================================
   LONG CHAU – THUỐC DATASET
   LAYER: STAGING / RAW
   NOTE:
   - Giữ nguyên tên bảng & tên cột theo file mô tả
   - Các cột “Và N cột hệ thống khác” được ASSUMED
   - Không PK / FK
   ============================================================ */

-- ============================================================
-- 1. PIM — SKU
-- ============================================================
CREATE TABLE dim_product_sku_pim_flc (
    code BIGINT,
    product_id BIGINT,
    name TEXT,
    name_ascii TEXT,
    short_name TEXT,
    eng_name TEXT,
    upc_code VARCHAR(50),
    upc_id BIGINT,
    type VARCHAR(50),
    industry_code BIGINT,
    industry_name VARCHAR(255),
    confirm_status VARCHAR(50),
    is_active BOOLEAN,
    creation_time TIMESTAMP,

    -- ASSUMED SYSTEM COLUMNS
    is_delete BOOLEAN,
    creation_by VARCHAR(100),
    last_modification_by VARCHAR(100),
    last_modification_time TIMESTAMP,
    note TEXT,
    question TEXT,
    reason TEXT,
    ref_code VARCHAR(100),
    replace_product VARCHAR(100),
    tenant_code VARCHAR(50),
    d VARCHAR(50)
);

-- ============================================================
-- 2. PIM — CATEGORY
-- ============================================================
CREATE TABLE dim_category_pim_flc (
    id VARCHAR(36),
    unique_id BIGINT,
    name TEXT,
    level INT
);

-- ============================================================
-- 3. PIM — PRODUCT ↔ CATEGORY MAP
-- ============================================================
CREATE TABLE dim_product_category_pim_flc (
    category_id VARCHAR(36),
    id BIGINT,
    product_id BIGINT
);

-- ============================================================
-- 4. PIM — PRODUCT ATTRIBUTES
-- ============================================================
CREATE TABLE dim_product_attributes_pim_flc (
    product_id BIGINT,
    attribute_name VARCHAR(255),
    attribute_option_id BIGINT,
    value TEXT
);

-- ============================================================
-- 5. PIM — PRODUCT MEASURES
-- ============================================================
CREATE TABLE dim_product_measures_pim_flc (
    id BIGINT,
    sku_id BIGINT,
    measure_unit_name VARCHAR(100),
    ratio BIGINT,
    measure_rate_name TEXT,

    -- ASSUMED SYSTEM COLUMNS
    measure_unit_id BIGINT,
    measure_rate_id BIGINT,
    is_default BOOLEAN,
    level INT,
    is_sell_default BOOLEAN,
    unique_id VARCHAR(50)
);

-- ============================================================
-- 6. PIM — PRODUCT TAXONOMIES
-- ============================================================
CREATE TABLE dim_product_taxonomies_pim_flc (
    sku_id BIGINT,
    taxonomy_id VARCHAR(36),
    taxonomy_name VARCHAR(255)
);

-- ============================================================
-- 7. CMS — PRODUCTS
-- ============================================================
CREATE TABLE dim_products_cms_flc (
    id BIGINT,
    web_name TEXT,
    slug TEXT,
    description TEXT,
    usage TEXT,
    dosage TEXT,
    adverse_effect TEXT,
    preservation TEXT,
    careful TEXT,
    ingredient TEXT,
    disease TEXT,

    -- ASSUMED CMS CONFIG COLUMNS
    is_approved BOOLEAN,
    heading_text TEXT,
    is_nature BOOLEAN,
    reference_source TEXT,
    short_description TEXT,
    category VARCHAR(255),
    sku VARCHAR(100),
    attributes TEXT,
    pim_name TEXT,
    status VARCHAR(50),
    redirect_url TEXT,
    is_visible BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    published_at TIMESTAMP,
    created_by_id BIGINT,
    updated_by_id BIGINT,
    last_merged_draft TIMESTAMP
);

-- ============================================================
-- 8. CMS — CATEGORIES
-- ============================================================
CREATE TABLE dim_categories_cms_flc (
    id BIGINT,
    name TEXT,
    full_path_slug TEXT,
    meta_title TEXT,
    meta_description TEXT,
    description TEXT,

    -- ASSUMED UI COLUMNS
    name_eng TEXT,
    short_description TEXT,
    note TEXT,
    score INT,
    type VARCHAR(50),
    level INT,
    is_deleted BOOLEAN,
    is_visible BOOLEAN,
    meta_social_title TEXT,
    meta_social_description TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    created_by_id BIGINT,
    updated_by_id BIGINT,
    product_suggestion_list_enable BOOLEAN
);

-- ============================================================
-- 9. CMS — ATTRIBUTE TYPES
-- ============================================================
CREATE TABLE dim_attribute_types_cms_flc (
    id BIGINT,
    name VARCHAR(255),
    slug TEXT,
    pim_id BIGINT,

    -- ASSUMED SYSTEM COLUMNS
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    created_by_id BIGINT,
    updated_by_id BIGINT
);

-- ============================================================
-- 10. CMS — PRODUCT ATTRIBUTES
-- ============================================================
CREATE TABLE dim_product_attributes_cms_flc (
    id BIGINT,
    name VARCHAR(255),
    slug TEXT,
    pim_id BIGINT,

    -- ASSUMED DISPLAY COLUMNS
    headline TEXT,
    score INT,
    is_show_badge BOOLEAN,
    score_badge VARCHAR(50),
    is_show_info BOOLEAN,
    description TEXT,
    short_description TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    created_by_id BIGINT,
    updated_by_id BIGINT
);

-- ============================================================
-- 11. OMS — ORDER DETAIL
-- ============================================================
CREATE TABLE fact_order_detail_oms_flc (
    order_id BIGINT,
    order_detail_id BIGINT,
    order_code VARCHAR(100),
    item_code VARCHAR(100),
    item_name TEXT,
    shop_code VARCHAR(50),
    quantity BIGINT,
    unit_name VARCHAR(50),
    _group_price DECIMAL(18,2),
    discount_type VARCHAR(50),
    tax_rate DECIMAL(5,2),

    -- ASSUMED BILL COLUMNS
    barcode VARCHAR(100),
    whs_code VARCHAR(50),
    unit_code VARCHAR(50),
    _group_total DECIMAL(18,2),
    _group_total_bill DECIMAL(18,2),
    _group_discount DECIMAL(18,2),
    _group_discount_promotion DECIMAL(18,2),
    _group_total_tax DECIMAL(18,2),
    is_promotion BOOLEAN,
    is_hot BOOLEAN,
    created_date TIMESTAMP,
    modified_date TIMESTAMP,
    line_code VARCHAR(50),
    whs_name VARCHAR(255),
    user_manual TEXT,
    reason_price_discount_code VARCHAR(100),
    note TEXT,
    point BIGINT,
    point_id BIGINT,
    is_inventory_management BOOLEAN,
    line_num INT,
    is_expired_date BOOLEAN,
    is_check_price BOOLEAN,
    meta_data TEXT,
    is_project BOOLEAN,
    is_special_control BOOLEAN,
    d VARCHAR(50)
);

/* =======================
   END OF FILE
   ======================= */