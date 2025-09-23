from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class SnowflakeConfig:
    account: str
    user: str
    password: str
    warehouse: str
    database: str
    schema: str
    role: Optional[str] = None
    stage_name: str = "%RIGHTMOVE_STAGE"
    staging_table: str = "RIGHTMOVE_STAGING"
    final_table: str = "RIGHTMOVE_ANALYSIS"


def load_config() -> SnowflakeConfig:
    return SnowflakeConfig(
        account=os.getenv("SNOWFLAKE_ACCOUNT", "ORG.ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER", ""),
        password=os.getenv("SNOWFLAKE_PASSWORD", ""),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE", "DB"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE", None),
        stage_name=os.getenv("SNOWFLAKE_STAGE_NAME", "%RIGHTMOVE_STAGE"),
        staging_table=os.getenv("SNOWFLAKE_TABLE_STAGING", "RIGHTMOVE_STAGING"),
        final_table=os.getenv("SNOWFLAKE_TABLE_FINAL", "RIGHTMOVE_ANALYSIS"),
    )


def main(argv: list[str]) -> int:
    cfg = load_config()
    # Mocked path if creds are missing
    if not (cfg.user and cfg.password):
        print("[mock] Snowflake credentials not set; printing COPY/MERGE plan instead.")
        print(f"USE WAREHOUSE {cfg.warehouse}; USE DATABASE {cfg.database}; USE SCHEMA {cfg.schema};")
        print(f"COPY INTO {cfg.staging_table} FROM @{cfg.stage_name}/rightmove/ FILE_FORMAT=(TYPE=CSV SKIP_HEADER=1);")
        print(
            f"MERGE INTO {cfg.final_table} t USING (SELECT * FROM {cfg.staging_table}) s "
            "ON t.rightmove_id = s.rightmove_id "
            "WHEN MATCHED THEN UPDATE SET t = OBJECT_CONSTRUCT_KEEPING_EXISTING(t, s) "
            "WHEN NOT MATCHED THEN INSERT VALUES (s.*);"
        )
        return 0

    try:
        import snowflake.connector  # type: ignore
    except Exception as e:
        print("snowflake-connector-python not installed.")
        return 2

    con = snowflake.connector.connect(
        account=cfg.account,
        user=cfg.user,
        password=cfg.password,
        warehouse=cfg.warehouse,
        database=cfg.database,
        schema=cfg.schema,
        role=cfg.role,
    )
    cur = con.cursor()
    try:
        cur.execute(f"USE WAREHOUSE {cfg.warehouse}")
        cur.execute(f"USE DATABASE {cfg.database}")
        cur.execute(f"USE SCHEMA {cfg.schema}")
        cur.execute(
            f"COPY INTO {cfg.staging_table} FROM @{cfg.stage_name}/rightmove/ FILE_FORMAT=(TYPE=CSV SKIP_HEADER=1) ON_ERROR='CONTINUE'"
        )
        cur.execute(
            f"""
            MERGE INTO {cfg.final_table} AS t
            USING (
                SELECT * FROM {cfg.staging_table}
            ) AS s
            ON t.rightmove_id = s.rightmove_id
            WHEN MATCHED THEN UPDATE SET
              price_value = COALESCE(s.price_value, t.price_value),
              price_currency = COALESCE(s.price_currency, t.price_currency),
              property_type = COALESCE(s.property_type, t.property_type),
              property_title = COALESCE(s.property_title, t.property_title),
              bedrooms = COALESCE(s.bedrooms, t.bedrooms),
              bathrooms = COALESCE(s.bathrooms, t.bathrooms),
              sizes = COALESCE(s.sizes, t.sizes),
              tenure = COALESCE(s.tenure, t.tenure),
              estate_agent = COALESCE(s.estate_agent, t.estate_agent),
              key_features = COALESCE(s.key_features, t.key_features),
              description = COALESCE(s.description, t.description),
              updated_at = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT VALUES (s.*)
            ;
            """
        )
        print("Load completed.")
        return 0
    finally:
        cur.close()
        con.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


