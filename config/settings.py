import os
import psutil
import onnxruntime

logical_cpu_count = psutil.cpu_count(logical=False)

ENV_VARS = {
    "OMP_NUM_THREADS": str(logical_cpu_count),
    "ONNXRUNTIME_THREAD_COUNT": str(logical_cpu_count),
    "OMP_WAIT_POLICY": "PASSIVE",
    "OMP_PROC_BIND": "CLOSE",
    "OMP_PLACES": "cores",
    "KMP_AFFINITY": "granularity=fine,compact,1,0",
    "OPENBLAS_NUM_THREADS": str(logical_cpu_count),
    "MKL_NUM_THREADS": str(logical_cpu_count),
    "VECLIB_MAXIMUM_THREADS": str(logical_cpu_count),
    "NUMEXPR_NUM_THREADS": str(logical_cpu_count),
    "ONNXRUNTIME_DISABLE_THREAD_AFFINITY": "1",
    "OMP_SCHEDULE": "static",
    "KMP_BLOCKTIME": "0",
    "KMP_SETTINGS": "0"
}

for key, value in ENV_VARS.items():
    os.environ[key] = value

onnxruntime.set_default_logger_severity(3)
ONNX_SESSION_OPTIONS = onnxruntime.SessionOptions()
ONNX_SESSION_OPTIONS.intra_op_num_threads = logical_cpu_count
ONNX_SESSION_OPTIONS.inter_op_num_threads = logical_cpu_count
ONNX_SESSION_OPTIONS.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
ONNX_SESSION_OPTIONS.enable_cpu_mem_arena = False
ONNX_SESSION_OPTIONS.enable_mem_pattern = False
ONNX_SESSION_OPTIONS.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_DISABLE_ALL
