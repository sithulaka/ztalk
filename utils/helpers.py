import sys
import readline

def get_user_input(prompt):
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting...")
        sys.exit(0)

def display_help():
    print("\nAvailable commands:")
    print("/list - Show connected peers")
    print("/msg <username> <message> - Send private message")
    print("/broadcast <message> - Send message to all")
    print("/quit - Exit program")