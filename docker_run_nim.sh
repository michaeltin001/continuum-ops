docker run -it --rm --gpus all \
  -p 8000:8000 \
  --shm-size=16GB \
  -v /opt/nim/loras:/opt/nim/loras \
  -e NGC_API_KEY="NVIDIA_API_KEY" \
  -e NIM_PEFT_SOURCE=/opt/nim/loras \
  -e NIM_PEFT_REFRESH_INTERVAL=10 \
  nvcr.io/nim/meta/llama-3.1-8b-instruct:latest \
  --max-model-len 21504