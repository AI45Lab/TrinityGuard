# Research Assistant System - Full Demo

This directory contains a complete implementation of a research assistant multi-agent system (MAS) using AG2/AutoGen.

## Overview

The research assistant system consists of 4 specialized agents working together to research academic papers, analyze their content, and generate comprehensive summaries.

## System Architecture

### Agents

1. **Coordinator** - Orchestrates the entire research workflow
   - Receives research requests from users
   - Breaks down tasks into clear steps
   - Delegates work to specialist agents
   - Monitors progress and presents final results

2. **Searcher** - Finds academic papers
   - Uses `search_papers` tool to find relevant papers
   - Reports search results with paper IDs and metadata
   - Recommends most relevant papers based on citations

3. **Analyzer** - Analyzes paper content
   - Uses `read_paper` tool to read full paper content
   - Uses `extract_keywords` tool to identify key themes
   - Synthesizes findings from multiple papers
   - Identifies common themes, risks, and recommendations

4. **Summarizer** - Creates research summaries
   - Compiles findings into coherent summaries
   - Structures summaries with clear sections
   - Uses `save_summary` tool to persist results

### Tools

1. **search_papers(query, max_results=5)** - Search for academic papers
   - Returns: JSON with paper IDs, titles, authors, abstracts, citations

2. **read_paper(paper_id)** - Read full paper content
   - Returns: JSON with paper title and detailed content

3. **extract_keywords(text)** - Extract keywords from text
   - Returns: JSON with categorized keywords

4. **save_summary(content, filename)** - Save summary to file
   - Returns: JSON with save status and file path

## Files

- `__init__.py` - Package initialization
- `tools.py` - Tool function implementations (4 tools)
- `step1_native_ag2.py` - Native AG2 MAS implementation

## Usage

### Running the Example

```bash
cd /home/kai/Projects/研二寒假/mas_safety/mas_level_safety/MASSafetyGuard/examples/full_demo
python step1_native_ag2.py
```

### Test Case

The system is tested with the following research query:

```
研究多智能体系统的安全风险，找出最新的3篇相关论文并总结主要发现。

Please:
1. Search for papers about multi-agent system safety risks
2. Select the top 3 most relevant papers
3. Read and analyze each paper
4. Extract key findings and safety risks
5. Create a comprehensive summary
6. Save the summary to 'mas_safety_research_summary.txt'
```

### Expected Workflow

1. User presents research query to Coordinator
2. Coordinator delegates search task to Searcher
3. Searcher uses `search_papers` tool to find papers
4. Coordinator delegates analysis to Analyzer
5. Analyzer uses `read_paper` and `extract_keywords` tools
6. Coordinator delegates summarization to Summarizer
7. Summarizer creates summary and uses `save_summary` tool
8. Coordinator presents final results to User

## Configuration

The system uses the project's LLM configuration from:
- `config/mas_llm_config.yaml`

Make sure this file exists and contains valid API credentials.

## Implementation Details

### Tool Registration

Tools are registered using AG2's `register_function` API:
- Each tool is assigned to specific agents (caller)
- User proxy acts as executor for all tools
- Tools use Python type annotations for parameter descriptions

### GroupChat Configuration

- **max_round**: 30 (maximum conversation rounds)
- **speaker_selection_method**: "auto" (LLM-based selection)
- **allow_repeat_speaker**: False (prevents consecutive turns)

### Termination Condition

The conversation terminates when the Coordinator says "RESEARCH COMPLETE" after the summary is saved.

## Mock Data

All tools return simulated data for demonstration purposes:
- 5 mock papers about multi-agent system safety
- Detailed paper content with findings and recommendations
- Keyword extraction based on pattern matching
- File saving to local filesystem

## Next Steps

This is Step 1 of the full demo. Subsequent steps will:
- Step 2: Wrap with Level 1 AG2MAS framework
- Step 3: Add Level 2 testing scaffolding
- Step 4: Integrate Level 3 safety monitoring
- Step 5: Create complete demonstration script
