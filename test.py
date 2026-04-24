import requests
image_prompt = "A cartoonish illustration of an Argentine family in a living room with an AI robot helping them, vibrant colors, cartoon style"
image_url = f"https://image.pollinations.ai/prompt/{image_prompt}?nologo=true"
response = requests.get(image_url)
print(response.status_code)
