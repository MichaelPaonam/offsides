# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AMD Developer Hackathon project. The hackathon focuses on building AI agents and high-performance AI applications on AMD GPUs in the cloud.

### Available Tracks

- **Track 1: AI Agents & Agentic Workflows** — Build intelligent AI systems that automate workflows, coordinate agents, or assist users. Frameworks: LangChain, CrewAI, AutoGen with open-source models (Llama, DeepSeek, Mistral, Qwen).
- **Track 2: Fine-Tuning on AMD GPUs** — Domain-specific LLM fine-tuning. Tech: ROCm, PyTorch, Hugging Face Optimum-AMD, vLLM.
- **Track 3: Vision & Multimodal AI** — Multi-data-type processing (images, video, audio). Models: Llama 3.2 Vision, Qwen-VL optimized for ROCm.

### Infrastructure

- AMD Developer Cloud with $100 credits
- AMD Instinct MI300X GPUs (cloud-accessible, no local hardware needed)
- ROCm (AMD's open-source GPU computing platform, equivalent to NVIDIA CUDA)

## Development Notes

- All compute runs in the cloud via AMD Developer Cloud — no local GPU required
- ROCm is the GPU software stack; use it instead of CUDA
- When using PyTorch, ensure ROCm-compatible versions are installed (`pip install torch --index-url https://download.pytorch.org/whl/rocm6.0`)
- Submission guidelines: https://lablab.ai/delivering-your-hackathon-solution
