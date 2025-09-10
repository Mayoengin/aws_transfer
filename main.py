"""
Main script to run the ReAct agent for Norm data queries.
"""

import sys
import logging
from simple_react_agent import SimpleReActAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)




def main():
    """Main interaction loop."""
    
    # Initialize the agent
    try:
        agent = SimpleReActAgent()
        logger.info("Simple ReAct agent initialized successfully")
    except Exception as e:
        print(f"Failed to initialize agent: {e}")
        sys.exit(1)
    
    # Main interaction loop
    while True:
        try:
            # Get user input
            user_query = input("\n🔍 Your query: ").strip()
            
            # Handle special commands
            if user_query.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not user_query:
                continue
            
            # Process the query
            print("\n⚙️  Processing your request...")
            
            response = agent.process_query(user_query)
            
            print("\n💬 Response:")
            print(response)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            print(f"\n❌ Error: {e}")
            print("Please try again or type 'exit' to quit.")


if __name__ == "__main__":
    main()