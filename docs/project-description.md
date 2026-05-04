# Offsides

## One-liner

A multimodal AI system that watches football and finds when prediction markets are wrong.

## Short Description

**Offsides** is a multimodal AI system that analyzes UEFA Champions League match footage alongside statistical data to detect when sports prediction markets are mispriced. Using Llama 3.2 Vision running on AMD MI300X GPUs, it extracts tactical signals from video frames — defensive shape, pressing intensity, transition patterns — that traditional stats-based models miss, then compares its probability estimates against market odds to surface edges the crowd hasn't priced in yet.

## Elevator Pitch (30 seconds)

Prediction markets price sports outcomes using statistics — xG, form, head-to-head records. But they've never had eyes. Offsides uses vision-language AI running on AMD MI300X GPUs to analyze match footage alongside traditional stats, extracting tactical signals that numbers alone miss — defensive shape, pressing intensity, transition patterns. When our visual intelligence disagrees with the market price, that's an edge.

## What It Does

Offsides is a multimodal pipeline that:

1. Ingests UEFA Champions League match highlight footage and structured match statistics
2. Extracts key frames and analyzes them using Llama 3.2 Vision for tactical insights (formations, compactness, pressing structure)
3. Combines visual analysis with statistical features (xG, fitness proxies, form data) into a unified match probability
4. Compares its assessment against historical prediction market odds to identify mispriced contracts

## The Problem

Sports prediction markets are efficient — but only within the modality they can process. They're built on structured data. Visual, tactical information (the kind a football analyst sees on screen) gets priced in slowly, through human intermediaries, or not at all.

## Our Approach

We treat multimodal AI as an information advantage. The same way satellite imagery creates alpha in commodity markets, match video creates alpha in sports prediction markets — if you can process it at scale.

## Tech Stack

- **Compute**: AMD Instinct MI300X (192GB HBM3) via AMD Developer Cloud
- **Model**: Llama 3.2 Vision on ROCm
- **Data**: StatsBomb (event-level match data), FBref (aggregate stats), historical betting odds
- **Video**: YouTube UEFA Champions League highlights
- **Pipeline**: Python, OpenCV, vLLM / Hugging Face Transformers

## Track

Track 3: Vision & Multimodal AI

## Why AMD

The MI300X's 192GB unified memory allows us to run the full 90B parameter vision model on a single device without sharding — critical for inference speed when processing multiple frames per match. ROCm provides native PyTorch compatibility, so our pipeline runs without CUDA-specific rewrites.
