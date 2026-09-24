FROM public.ecr.aws/lambda/python:3.12

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared app code (needed by document_processor service)
COPY app ${LAMBDA_TASK_ROOT}/app

# Copy Lambda handler
COPY lambda/document_processor/handler.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.lambda_doc_handler"]
