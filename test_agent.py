#!/usr/bin/env python3
"""
Test script for the simplified ReAct agent
"""

from react_agent import ReActAgent
import logging

logging.basicConfig(level=logging.DEBUG)

def test_agent():
    """Test the ReAct agent with sample queries."""
    
    print("="*50)
    print("Testing Simplified ReAct Agent")
    print("="*50)
    
    agent = ReActAgent()
    
    # Test queries
    test_queries = [
        "show me info about SRMECH01",
        "get device information for CEAWPDGA05"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-"*40)
        try:
            response = agent.process_query(query)
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")
        print("-"*40)

if __name__ == "__main__":
    test_agent()