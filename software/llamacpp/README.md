1. Provide your model information.

Before request the service, provide your own huggingface model URL and name in "hf_repo_id" and "hf_filename" parameters.

For example:
```
slapos request llamacpp ~/srv/project/slapos/software/llamacpp/software-cuda.cfg --parameters port=8083 \
  threads=16 \
  threads-batch=16\
  ctx=8192\
  batch=2048 \
  micro-batch=2048 \
  cache-type-k="q8_0" \
  cache-type-v="q8_0" \
  ngl=999 \
  embedding=0 \
  hf_repo_id="unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF" \
  hf_filename="Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf"
```

2. llama.cpp parameters setting

For the parameters that running the llama.cpp, you can check instance-input-schema.json to see the provided options. You can check llama.cpp's docs to understand it better.

3. Install the service

When you requesting the llama.cpp service, make sure you are using one of the software-cpu.cfg, software-cuda.cfg, software-vulkan.cfg. Do not use the plain software.cfg.

- software-cpu.cfg: Deploy and run llama.cpp purely on CPU
- software-cuda.cfg: Deploy and run llama.cpp on Nvidia GPU
- software-vulkan.cfg: Deploy and run llama.cpp on AMD Ryzen AI Max+ platform
