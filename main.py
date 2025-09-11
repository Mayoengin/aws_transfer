"""
Main script to run the ReAct agent for Norm data queries - AWS Bedrock version.
"""

import sys
import logging
from simple_react_agent import SimpleReActAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_aws_setup():
    """Check if AWS is properly configured."""
    try:
        import boto3
        # Try to create a client to test credentials
        client = boto3.client('bedrock-runtime', region_name='eu-central-1')
        return True
    except Exception as e:
        print(f"❌ AWS setup issue: {e}")
        print("\n🔧 To fix this:")
        print("1. Install AWS CLI: brew install awscli")
        print("2. Configure AWS: aws configure")
        print("3. Make sure you have access to Bedrock in AWS console")
        return False


def main():
    """Main interaction loop."""
    
    print("🚀 Starting TANIA - AWS Bedrock ReAct Agent")
    
    # Check AWS setup first
    if not check_aws_setup():
        print("\n❌ Please fix AWS configuration before continuing.")
        sys.exit(1)
    
    # Initialize the agent
    try:
        agent = SimpleReActAgent()
        logger.info("Simple ReAct agent initialized successfully")
        print("✅ Agent ready!")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
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
            if "AccessDenied" in str(e):
                print("💡 Tip: Check your AWS Bedrock model access in the console")
            elif "credentials" in str(e).lower():
                print("💡 Tip: Run 'aws configure' to set up your credentials")
            print("Please try again or type 'exit' to quit.")


if __name__ == "__main__":
    main()