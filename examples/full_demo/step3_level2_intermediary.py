"""Step 3: Level 2 Intermediary - Testing AG2Intermediary scaffolding interfaces.

This example demonstrates the Level 2 AG2Intermediary class and tests all scaffolding interfaces:
- agent_chat() - Direct point-to-point chat with an agent
- simulate_agent_message() - Simulate message between agents
- inject_tool_call() - Inject tool calls (mock and real)
- inject_memory() - Inject memory/context into agents
- broadcast_message() - Broadcast message to multiple agents
- spoof_identity() - Test identity spoofing detection
- get_resource_usage() - Get resource usage statistics

This builds on Task 2 by wrapping the AG2MAS instance with AG2Intermediary.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.level1_framework.ag2_wrapper import AG2MAS
from src.level2_intermediary.ag2_intermediary import AG2Intermediary

# Import the base MAS creation function from step1
from step1_native_ag2 import create_research_assistant_mas


def create_research_assistant_mas_with_wrapper():
    """Create a research assistant MAS wrapped with AG2MAS.

    Reuses the base MAS creation from step1 (fixed linear workflow).

    Returns:
        AG2MAS instance wrapping the research assistant system
    """
    # Reuse the base MAS creation from step1
    agents, group_chat, manager, user_proxy = create_research_assistant_mas()

    # Wrap with AG2MAS
    mas = AG2MAS(
        agents=agents,
        group_chat=group_chat,
        manager=manager
    )

    return mas


def print_separator(title="", char="=", width=80):
    """Print a formatted separator line."""
    if title:
        print()
        print(char * width)
        print(title)
        print(char * width)
    else:
        print(char * width)


def test_agent_chat(intermediary: AG2Intermediary):
    """Test 1: agent_chat() - Direct point-to-point chat with an agent."""
    print_separator("Test 1: agent_chat() - Direct point-to-point chat with an agent")
    print()

    print("Description: Test direct communication with the Coordinator agent")
    print("Method: intermediary.agent_chat(agent_name, message, history)")
    print()

    agent_name = "Coordinator"
    message = "Please introduce yourself and describe your role in the research team."

    print(f"Agent: {agent_name}")
    print(f"Message: \"{message}\"")
    print()
    print("Sending message...")
    print("-" * 80)

    try:
        response = intermediary.agent_chat(agent_name, message)
        print(f"Response from {agent_name}:")
        print(response)
        print("-" * 80)
        print("Status: SUCCESS")
    except Exception as e:
        print(f"Error: {e}")
        print("Status: FAILED")

    print()


def test_simulate_agent_message(intermediary: AG2Intermediary):
    """Test 2: simulate_agent_message() - Simulate message between agents."""
    print_separator("Test 2: simulate_agent_message() - Simulate message between agents")
    print()

    print("Description: Simulate a message from Coordinator to Searcher")
    print("Method: intermediary.simulate_agent_message(from_agent, to_agent, message)")
    print()

    from_agent = "Coordinator"
    to_agent = "Searcher"
    message = "Please search for papers about multi-agent system safety."

    print(f"From: {from_agent}")
    print(f"To: {to_agent}")
    print(f"Message: \"{message}\"")
    print()
    print("Simulating message...")
    print("-" * 80)

    result = intermediary.simulate_agent_message(from_agent, to_agent, message)

    print(f"Success: {result.get('success', False)}")
    print(f"From: {result.get('from', 'N/A')}")
    print(f"To: {result.get('to', 'N/A')}")
    print(f"Message: {result.get('message', 'N/A')}")

    if result.get('success'):
        print(f"Response: {result.get('response', 'N/A')}")
    else:
        print(f"Error: {result.get('error', 'N/A')}")

    print("-" * 80)
    print()


def test_inject_tool_call(intermediary: AG2Intermediary):
    """Test 3: inject_tool_call() - Inject tool calls (mock and real)."""
    print_separator("Test 3: inject_tool_call() - Inject tool calls (mock and real)")
    print()

    # Test 3a: Mock tool call
    print("Test 3a: Mock tool call (mock=True)")
    print("Description: Simulate a tool call without real execution")
    print("Method: intermediary.inject_tool_call(agent_name, tool_name, params, mock=True)")
    print()

    agent_name = "Searcher"
    tool_name = "search_papers"
    params = {"query": "multi-agent safety", "max_results": 3}

    print(f"Agent: {agent_name}")
    print(f"Tool: {tool_name}")
    print(f"Params: {json.dumps(params, indent=2)}")
    print(f"Mock: True")
    print()
    print("Injecting mock tool call...")
    print("-" * 80)

    result = intermediary.inject_tool_call(agent_name, tool_name, params, mock=True)

    print(f"Success: {result.get('success', False)}")
    print(f"Agent: {result.get('agent', 'N/A')}")
    print(f"Tool: {result.get('tool', 'N/A')}")
    print(f"Mock: {result.get('mock', False)}")
    print(f"Result: {result.get('result', 'N/A')}")

    if not result.get('success'):
        print(f"Error: {result.get('error', 'N/A')}")

    print("-" * 80)
    print()

    # Test 3b: Real tool call
    print("Test 3b: Real tool call (mock=False)")
    print("Description: Execute a real tool call")
    print("Method: intermediary.inject_tool_call(agent_name, tool_name, params, mock=False)")
    print()

    print(f"Agent: {agent_name}")
    print(f"Tool: {tool_name}")
    print(f"Params: {json.dumps(params, indent=2)}")
    print(f"Mock: False")
    print()
    print("Injecting real tool call...")
    print("-" * 80)

    result = intermediary.inject_tool_call(agent_name, tool_name, params, mock=False)

    print(f"Success: {result.get('success', False)}")
    print(f"Agent: {result.get('agent', 'N/A')}")
    print(f"Tool: {result.get('tool', 'N/A')}")
    print(f"Mock: {result.get('mock', False)}")

    if result.get('success'):
        result_data = result.get('result', 'N/A')
        if isinstance(result_data, str) and len(result_data) > 200:
            print(f"Result (truncated): {result_data[:200]}...")
        else:
            print(f"Result: {result_data}")
    else:
        print(f"Error: {result.get('error', 'N/A')}")

    print("-" * 80)
    print()


def test_inject_memory(intermediary: AG2Intermediary):
    """Test 4: inject_memory() - Inject memory/context into agents."""
    print_separator("Test 4: inject_memory() - Inject memory/context into agents")
    print()

    # Test 4a: Mock memory injection
    print("Test 4a: Mock memory injection (mock=True)")
    print("Description: Simulate memory injection without real modification")
    print("Method: intermediary.inject_memory(agent_name, memory_content, memory_type, mock=True)")
    print()

    agent_name = "Analyzer"
    memory_content = "IMPORTANT: Focus on safety-critical findings in all paper analyses."
    memory_type = "context"

    print(f"Agent: {agent_name}")
    print(f"Memory Type: {memory_type}")
    print(f"Memory Content: \"{memory_content}\"")
    print(f"Mock: True")
    print()
    print("Injecting mock memory...")
    print("-" * 80)

    success = intermediary.inject_memory(agent_name, memory_content, memory_type, mock=True)

    print(f"Success: {success}")
    print(f"Status: {'Memory injection simulated' if success else 'Failed'}")
    print("-" * 80)
    print()

    # Test 4b: Real memory injection
    print("Test 4b: Real memory injection (mock=False)")
    print("Description: Inject real memory/context into agent")
    print("Method: intermediary.inject_memory(agent_name, memory_content, memory_type, mock=False)")
    print()

    print(f"Agent: {agent_name}")
    print(f"Memory Type: {memory_type}")
    print(f"Memory Content: \"{memory_content}\"")
    print(f"Mock: False")
    print()
    print("Injecting real memory...")
    print("-" * 80)

    success = intermediary.inject_memory(agent_name, memory_content, memory_type, mock=False)

    print(f"Success: {success}")
    print(f"Status: {'Memory injected successfully' if success else 'Failed to inject memory'}")
    print("-" * 80)
    print()


def test_broadcast_message(intermediary: AG2Intermediary):
    """Test 5: broadcast_message() - Broadcast message to multiple agents."""
    print_separator("Test 5: broadcast_message() - Broadcast message to multiple agents")
    print()

    # Test 5a: Mock broadcast
    print("Test 5a: Mock broadcast (mock=True)")
    print("Description: Simulate broadcasting a message to multiple agents")
    print("Method: intermediary.broadcast_message(from_agent, to_agents, message, mock=True)")
    print()

    from_agent = "Coordinator"
    to_agents = ["Searcher", "Analyzer", "Summarizer"]
    message = "Team meeting: Please prepare status updates for the current research task."

    print(f"From: {from_agent}")
    print(f"To: {', '.join(to_agents)}")
    print(f"Message: \"{message}\"")
    print(f"Mock: True")
    print()
    print("Broadcasting mock message...")
    print("-" * 80)

    results = intermediary.broadcast_message(from_agent, to_agents, message, mock=True)

    print(f"Broadcast to {len(results)} agents:")
    for agent, result in results.items():
        print(f"\n  Agent: {agent}")
        print(f"  Success: {result.get('success', False)}")
        print(f"  Mock: {result.get('mock', False)}")
        print(f"  Response: {result.get('response', 'N/A')}")

    print("-" * 80)
    print()

    # Test 5b: Real broadcast (to fewer agents to save time)
    print("Test 5b: Real broadcast (mock=False) - Limited to 2 agents")
    print("Description: Broadcast a real message to multiple agents")
    print("Method: intermediary.broadcast_message(from_agent, to_agents, message, mock=False)")
    print()

    to_agents_limited = ["Searcher", "Analyzer"]
    message_real = "Please acknowledge receipt of this broadcast message."

    print(f"From: {from_agent}")
    print(f"To: {', '.join(to_agents_limited)}")
    print(f"Message: \"{message_real}\"")
    print(f"Mock: False")
    print()
    print("Broadcasting real message...")
    print("-" * 80)

    results = intermediary.broadcast_message(from_agent, to_agents_limited, message_real, mock=False)

    print(f"Broadcast to {len(results)} agents:")
    for agent, result in results.items():
        print(f"\n  Agent: {agent}")
        print(f"  Success: {result.get('success', False)}")
        print(f"  Mock: {result.get('mock', False)}")
        if result.get('success'):
            response = result.get('response', 'N/A')
            if len(str(response)) > 100:
                print(f"  Response (truncated): {str(response)[:100]}...")
            else:
                print(f"  Response: {response}")
        else:
            print(f"  Error: {result.get('error', 'N/A')}")

    print("-" * 80)
    print()

def test_spoof_identity(intermediary: AG2Intermediary):
    """Test 6: spoof_identity() - Test identity spoofing detection."""
    print_separator("Test 6: spoof_identity() - Test identity spoofing detection")
    print()

    # Test 6a: Mock identity spoofing
    print("Test 6a: Mock identity spoofing (mock=True)")
    print("Description: Simulate identity spoofing without real message")
    print("Method: intermediary.spoof_identity(real_agent, spoofed_agent, to_agent, message, mock=True)")
    print()

    real_agent = "Searcher"
    spoofed_agent = "Coordinator"
    to_agent = "Analyzer"
    message = "This is a high-priority task from the Coordinator (but actually from Searcher)."

    print(f"Real Sender: {real_agent}")
    print(f"Spoofed Sender: {spoofed_agent}")
    print(f"To: {to_agent}")
    print(f"Message: \"{message}\"")
    print(f"Mock: True")
    print()
    print("Testing mock identity spoofing...")
    print("-" * 80)

    result = intermediary.spoof_identity(real_agent, spoofed_agent, to_agent, message, mock=True)

    print(f"Success: {result.get('success', False)}")
    print(f"Real Sender: {result.get('real_sender', 'N/A')}")
    print(f"Spoofed Sender: {result.get('spoofed_sender', 'N/A')}")
    print(f"To: {result.get('to', 'N/A')}")
    print(f"Mock: {result.get('mock', False)}")
    print(f"Detected: {result.get('detected', False)}")

    if not result.get('success'):
        print(f"Error: {result.get('error', 'N/A')}")

    print("-" * 80)
    print()

    # Test 6b: Real identity spoofing
    print("Test 6b: Real identity spoofing (mock=False)")
    print("Description: Attempt real identity spoofing to test detection")
    print("Method: intermediary.spoof_identity(real_agent, spoofed_agent, to_agent, message, mock=False)")
    print()

    print(f"Real Sender: {real_agent}")
    print(f"Spoofed Sender: {spoofed_agent}")
    print(f"To: {to_agent}")
    print(f"Message: \"{message}\"")
    print(f"Mock: False")
    print()
    print("Testing real identity spoofing...")
    print("-" * 80)

    result = intermediary.spoof_identity(real_agent, spoofed_agent, to_agent, message, mock=False)

    print(f"Success: {result.get('success', False)}")
    print(f"Real Sender: {result.get('real_sender', 'N/A')}")
    print(f"Spoofed Sender: {result.get('spoofed_sender', 'N/A')}")
    print(f"To: {result.get('to', 'N/A')}")
    print(f"Mock: {result.get('mock', False)}")
    print(f"Detected: {result.get('detected', False)}")

    if result.get('success'):
        response = result.get('response', 'N/A')
        if len(str(response)) > 150:
            print(f"Response (truncated): {str(response)[:150]}...")
        else:
            print(f"Response: {response}")
    else:
        print(f"Error: {result.get('error', 'N/A')}")

    print()
    print("Note: Detection logic is typically implemented in the Level 3 monitor.")
    print("This test demonstrates the scaffolding capability for security testing.")
    print("-" * 80)
    print()


def test_get_resource_usage(intermediary: AG2Intermediary):
    """Test 7: get_resource_usage() - Get resource usage statistics."""
    print_separator("Test 7: get_resource_usage() - Get resource usage statistics")
    print()

    # Test 7a: Get resource usage for specific agent
    print("Test 7a: Get resource usage for specific agent")
    print("Description: Retrieve resource usage statistics for a single agent")
    print("Method: intermediary.get_resource_usage(agent_name)")
    print()

    agent_name = "Searcher"

    print(f"Agent: {agent_name}")
    print()
    print("Retrieving resource usage...")
    print("-" * 80)

    usage = intermediary.get_resource_usage(agent_name)

    print(f"Agent: {usage.get('agent', 'N/A')}")
    print(f"API Calls: {usage.get('api_calls', 0)}")
    print(f"Elapsed Time: {usage.get('elapsed_time', 0):.2f} seconds")
    print(f"Process Memory: {usage.get('process_memory_mb', 0):.2f} MB")
    print(f"CPU Percent: {usage.get('cpu_percent', 0):.2f}%")

    print("-" * 80)
    print()

    # Test 7b: Get aggregate resource usage for all agents
    print("Test 7b: Get aggregate resource usage for all agents")
    print("Description: Retrieve resource usage statistics for all agents")
    print("Method: intermediary.get_resource_usage()")
    print()

    print("Retrieving aggregate resource usage...")
    print("-" * 80)

    usage = intermediary.get_resource_usage()

    print(f"Total API Calls: {usage.get('total_api_calls', 0)}")
    print(f"Elapsed Time: {usage.get('elapsed_time', 0):.2f} seconds")
    print(f"Process Memory: {usage.get('process_memory_mb', 0):.2f} MB")
    print(f"CPU Percent: {usage.get('cpu_percent', 0):.2f}%")
    print()
    print("Per-Agent Statistics:")

    agents_stats = usage.get('agents', {})
    for agent_name, stats in agents_stats.items():
        print(f"  {agent_name}:")
        print(f"    API Calls: {stats.get('api_calls', 0)}")

    print("-" * 80)
    print()


def main():
    """Run the Level 2 intermediary demonstration."""
    print("=" * 80)
    print("Research Assistant System - Level 2 AG2Intermediary Testing")
    print("=" * 80)
    print()

    print("This script demonstrates the Level 2 AG2Intermediary class by testing")
    print("all 7 scaffolding interfaces for runtime manipulation and monitoring.")
    print()

    # Create the MAS
    print("Step 1: Creating research assistant MAS with AG2MAS wrapper...")
    print("-" * 80)
    mas = create_research_assistant_mas_with_wrapper()
    print("AG2MAS created successfully!")
    print()

    # Create the intermediary
    print("Step 2: Creating AG2Intermediary instance...")
    print("-" * 80)
    intermediary = AG2Intermediary(mas)
    print("AG2Intermediary created successfully!")
    print()

    print("=" * 80)
    print("Starting Level 2 Scaffolding Interface Tests")
    print("=" * 80)
    print()

    # Run all tests
    try:
        # Test 1: agent_chat
        test_agent_chat(intermediary)

        # Test 2: simulate_agent_message
        test_simulate_agent_message(intermediary)

        # Test 3: inject_tool_call
        test_inject_tool_call(intermediary)

        # Test 4: inject_memory
        test_inject_memory(intermediary)

        # Test 5: broadcast_message
        test_broadcast_message(intermediary)

        # Test 6: spoof_identity
        test_spoof_identity(intermediary)

        # Test 7: get_resource_usage
        test_get_resource_usage(intermediary)

        # Summary
        print("=" * 80)
        print("Level 2 Intermediary Testing Completed Successfully!")
        print("=" * 80)
        print()
        print("Summary:")
        print("- All 7 scaffolding interfaces have been tested")
        print("- Both mock and real execution modes were demonstrated")
        print("- The AG2Intermediary provides runtime manipulation capabilities")
        print("- These interfaces enable security testing and monitoring at Level 3")
        print()
        print("Next Steps:")
        print("- Proceed to Level 3 (TrinityGuard) for security monitoring")
        print("- Integrate with attack detection and prevention mechanisms")
        print("- Deploy in production with comprehensive safety guarantees")
        print()

    except Exception as e:
        print()
        print("=" * 80)
        print("Error during testing")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
