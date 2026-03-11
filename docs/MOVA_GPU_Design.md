# MOVA Node GPU Selection and Memory Management Design

**Version**: 1.0  
**Date**: 2025-03-11  
**Applicable Models**: MOVA-360p, MOVA-720p

---

## 1. Overview

MOVA (Multi-modal Omni-modal Video generation with Audio) nodes support multi-GPU selection, but due to model limitations, memory management requires special handling.

This document details the GPU selection mechanism, memory management strategy, and recommended configurations for MOVA nodes.

---

## 2. Memory Requirements

MOVA-360p model requires approximately **48GB VRAM** for full loading.

### 2.1 VRAM Requirements by Offload Mode

| Mode | VRAM Required | System RAM | Suitable GPUs | Speed | Use Case |
|------|--------------|------------|---------------|-------|----------|
| `none` | **48GB+** | Low | A6000, A100, H100 | Fastest | Large VRAM GPUs |
| `group` | **~12GB** | Medium | RTX 4090, RTX 5090 (32GB) | Fast | **Recommended** |
| `cpu` | **~4GB** | **48GB+** | Any GPU + Large RAM | Slow | Low VRAM fallback |

### 2.2 Key Points

- **32GB GPU (e.g., RTX 5090)**: Must use `group` mode, otherwise OOM occurs
- **48GB+ GPU (e.g., A6000)**: Can use `none` mode for best performance
- **CPU Mode**: Lowest VRAM requirement but slowest, requires large system RAM

---

## 3. GPU Selection Interface

### 3.1 RunningHub MOVA Loader Node Parameters

#### device (Dropdown)
- **Options**: `cuda:0`, `cuda:1`, `cuda:2`, `cuda:3`, ... (based on available GPUs)
- **Default**: `cuda:0`
- **Purpose**: Specify the primary GPU for model loading

#### additional_devices (Text Input)
- **Default**: `""` (empty string)
- **Format**: Comma-separated GPU list
- **Example**: `cuda:1,cuda:2,cuda:3`
- **Purpose**: Experimental multi-GPU support
- **Note**: Current MOVA mainly uses single GPU; additional_devices is reserved for future expansion

#### offload_mode (Dropdown)
- **`group`** (Recommended): Group offload, ~12GB VRAM, suitable for RTX 5090
- `cpu`: CPU offload, ~4GB VRAM but requires 48GB+ system RAM
- `none`: No offload, 48GB+ VRAM required, auto-switches to `group` if insufficient

---

## 4. Auto-Switch Logic

### 4.1 Smart OOM Protection

Built-in intelligent switching to prevent out-of-memory errors:

```python
# For single GPU with 32GB, group offload is REQUIRED
if device_ids is None or len(device_ids) <= 1:
    if offload_mode == "none":
        print(f"[MOVA] WARNING: offload_mode='none' requires 48GB+ VRAM. Auto-switching to 'group' mode.")
        offload_mode = "group"
```

### 4.2 Switching Scenarios

| Scenario | User Selection | Actual Execution | Reason |
|----------|---------------|------------------|---------|
| Single GPU | `none` | -> `group` | Insufficient VRAM, auto-switch |
| Single GPU | `group` | `group` | Normal execution |
| Single GPU | `cpu` | `cpu` | Normal execution |
| Multi GPU | `none` | -> `group` | Auto-switch on multi-GPU load failure |

---

## 5. Multi-GPU Support Limitations

### 5.1 Current Limitations

- **Model Design**: MOVA is primarily designed for single-GPU operation
- **Multi-GPU Implementation**: Relies on `accelerate` library's `device_map="balanced"`
- **Failure Handling**: Falls back to single GPU + `group` mode on multi-GPU load failure

### 5.2 Multi-GPU Loading Flow

```
1. User selects multi-GPU (device: cuda:0, additional_devices: cuda:1,cuda:2,cuda:3)
2. Code attempts to load using accelerate's device_map="balanced"
3. If successful: Model shards across multiple GPUs
4. If failed: Logs error, falls back to single GPU + group mode
```

### 5.3 Typical Log Output

```
[MOVA] Multi-GPU mode: [0, 1, 2, 3]
[MOVA] Attempting multi-GPU load with device_map='balanced'
[MOVA] Multi-GPU load failed: xxx (error message)
[MOVA] Falling back to single-GPU mode
[MOVA] Auto-switching to 'group' offload mode
[MOVA] Model loaded with group offload (~12GB VRAM)
```

---

## 6. Recommended Configurations

### 6.1 Single RTX 5090 (32GB) - Recommended

```
offload_mode: group        REQUIRED
device: cuda:0
additional_devices:        (leave empty)
```

**Notes**:
- VRAM usage: ~12GB
- Inference speed: Fast
- No multi-GPU coordination needed

### 6.2 Multi-GPU Server (4x RTX 5090) - Experimental

```
offload_mode: group        Recommended even for multi-GPU
device: cuda:0
additional_devices: cuda:1,cuda:2,cuda:3  (experimental)
```

**Notes**:
- Multi-GPU support is experimental
- Falls back to single GPU if multi-GPU loading fails
- Group mode is efficient even with multiple GPUs available

### 6.3 Large VRAM GPU (A100 80GB) - High Performance

```
offload_mode: none         Can fully load to GPU
device: cuda:0
additional_devices:
```

**Notes**:
- VRAM usage: 48GB+
- Inference speed: Fastest
- No offload overhead

---

## 7. Memory Management Implementation

### 7.1 Pre-Loading Cleanup

```python
# Clear GPU cache and garbage collection
torch.cuda.empty_cache()
gc.collect()
```

### 7.2 Low Memory Loading

```python
# Use low_cpu_mem_usage to reduce loading memory spikes
pipe = MOVA.from_pretrained(
    model_path, 
    torch_dtype=torch_dtype, 
    local_files_only=True,
    low_cpu_mem_usage=True,
)
```

### 7.3 Group Offload Strategy

```python
# Group offload configuration
pipe.enable_group_offload(
    onload_device=device,
    offload_device=torch.device("cpu"),
    offload_type="leaf_level",
    use_stream=True,
    low_cpu_mem_usage=True,
)
```

---

## 8. Troubleshooting Guide

### 8.1 OOM Error (Out of Memory)

**Symptoms**:
```
Allocation on device X would exceed allowed memory. (out of memory)
Currently allocated     : 30.77 GiB
Requested               : 50.00 MiB
Device limit            : 31.36 GiB
```

**Solution**:
1. Ensure `offload_mode: group` is selected
2. If `none` was selected, code auto-switches to `group`
3. Check for other programs using VRAM
4. Restart ComfyUI to clear VRAM

### 8.2 Multi-GPU Load Failure

**Symptoms**:
```
[MOVA] Multi-GPU load failed: auto not supported. Supported strategies are: balanced, cuda, cpu
[MOVA] Falling back to single-GPU mode
```

**Solution**:
- Normal behavior, automatically falls back to single GPU + group mode
- No manual intervention needed
- Single GPU performance is sufficient

### 8.3 CPU Mode Too Slow

**Symptoms**:
- Generation speed significantly slower than expected
- High system memory usage

**Solution**:
1. Switch to `group` mode
2. Ensure GPU has sufficient VRAM (32GB)
3. If CPU mode is required, ensure system RAM >= 48GB

### 8.4 Slow Model Loading

**Symptoms**:
- MOVA Loader node takes long time to execute

**Solution**:
1. First load reads model files, subsequent loads are faster
2. Ensure model files are on SSD
3. Verify `low_cpu_mem_usage=True` is in effect

---

## 9. Implementation Checklist

### 9.1 Environment Setup
- [ ] Install `accelerate` library: `pip install accelerate` (optional, for multi-GPU)
- [ ] Verify MOVA model downloaded to `ComfyUI/models/MOVA/`
- [ ] Confirm GPU driver and CUDA version compatibility

### 9.2 Configuration Validation
- [ ] Test `group` mode single-GPU operation
- [ ] Check VRAM usage around ~12GB
- [ ] Verify generation results are correct

### 9.3 Multi-GPU Testing (Optional)
- [ ] Attempt multi-GPU configuration
- [ ] Observe success or automatic fallback
- [ ] Compare single GPU vs multi-GPU performance

---

## 10. Technical Details

### 10.1 Code File Locations
- Node definition: `/mnt/data/project/ComfyUI/custom_nodes/ComfyUI_RH_MOVA/nodes.py`
- Model loading: `/mnt/data/project/ComfyUI/custom_nodes/ComfyUI_RH_MOVA/mova_wrapper.py`

### 10.2 Key Functions
- `get_available_devices()`: Get available GPU list
- `load_mova_pipeline()`: Load MOVA model
- `enable_group_offload()`: Enable group offload

### 10.3 Dependencies
- `torch`: PyTorch base
- `diffusers`: MOVA model based on diffusers
- `accelerate`: Multi-GPU support (optional)

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-03-11 | Initial version, added GPU selection and multi-GPU support |

---

## 12. References

- MOVA Official Repository: https://github.com/OpenMOSS/MOVA
- Diffusers Documentation: https://huggingface.co/docs/diffusers
- Accelerate Multi-GPU: https://huggingface.co/docs/accelerate

---

**Note**: MOVA model is continuously updated; this document is based on current implementation. For changes, refer to latest code.
