from src.infrastructure.review_suggestions.redis_serde import decode_stream_payload_fields


def test_decode_stream_job_fields_accepts_str_payload() -> None:
    fields = {
        "payload": '{"job_type":"rebuild_product_profile","product_id":"550e8400-e29b-41d4-a716-446655440000"}'
    }
    job = decode_stream_payload_fields(fields)
    assert job["job_type"] == "rebuild_product_profile"
