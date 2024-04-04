FROM python: 3.9.6 slim

# Set the working directory in the container
WORKDIR /app 

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any dependencies
RUN pip install -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY . .

# Specify the command to run on container start
CMD [ "python", "./app.py" ]

# Build the Docker image
docker build -t my-python-app .

# Run the Docker container
docker run my-python-app