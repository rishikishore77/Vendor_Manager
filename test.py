
from datetime import datetime


def parse_time_ampm(time_str):

    return datetime.strptime(time_str.strip(), '%I:%M %p').time()

if __name__ == "__main__":
    # Example usage
    time_str = "02:30 PM"
    parsed_time = parse_time_ampm(time_str)
    print(f"Parsed time: {parsed_time}")  # Output: Parsed time: 14:30:00