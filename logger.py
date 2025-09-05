from crashlens_logger import CrashLensLogger
import uuid
from datetime import datetime
import openai

logger = CrashLensLogger()

def call_and_log():
    trace_id = str(uuid.uuid4())
    start_time = datetime.utcnow().isoformat() + "Z"
    prompt = "What are the main tourist attractions in Rome?"
    model = "gpt-3.5-turbo"
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    end_time = datetime.utcnow().isoformat() + "Z"
    usage = response["usage"]
    logger.log_event(
        traceId=trace_id,
        startTime=start_time,
        endTime=end_time,
        input={"model": model, "prompt": prompt},
        usage=usage,
        output_file="logs.jsonl"  # <-- This will create/append to logs.jsonl
    )