Before request the service, provide your own model first.

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

The default model is an embedding model which was downloaded in the software stage.
