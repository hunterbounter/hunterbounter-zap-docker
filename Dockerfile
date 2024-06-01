FROM zaproxy/zap-stable

USER root

# INstall python3 and pip3
RUN apt-get update && apt-get install -y python3 python3-pip

# Copy the application
COPY . /zap-telemetry

 

# Install the application
WORKDIR /zap-telemetry
RUN pip3 install -r req.txt

# Copy the start_services.sh script
COPY start_services.sh /start_services.sh
RUN chmod +x /start_services.sh

# Run the start_services.sh script
ENTRYPOINT ["/start_services.sh"]
