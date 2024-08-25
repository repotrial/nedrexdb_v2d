#!/bin/bash

# The path to your neo4j.conf file
NEO4J_CONF="/var/lib/neo4j/conf/neo4j.conf"

# The desired number of allowed failed authentication attempts
MAX_FAILED_ATTEMPTS=100

# Uncomment the dbms.security.auth_max_failed_attempts line and set its value
if grep -q "^#*dbms.security.auth_max_failed_attempts=" "$NEO4J_CONF"; then
    sed -i "s/^#*dbms.security.auth_max_failed_attempts=.*/dbms.security.auth_max_failed_attempts=$MAX_FAILED_ATTEMPTS/g" "$NEO4J_CONF"
else
    echo "dbms.security.auth_max_failed_attempts=$MAX_FAILED_ATTEMPTS" >> "$NEO4J_CONF"
fi

# Check if Bolt connector is enabled in neo4j.conf
if grep -q "^#*dbms.connector.bolt.enabled=" "$NEO4J_CONF"; then
    # If the line is present, uncomment it
    sed -i "s/^#*dbms.connector.bolt.enabled=.*/dbms.connector.bolt.enabled=true/g" "$NEO4J_CONF"
    echo "Bolt connector enabled in neo4j.conf."
else
    # If the line is not present, add it
    echo "dbms.connector.bolt.enabled=true" >> "$NEO4J_CONF"
    echo "Added dbms.connector.bolt.enabled to neo4j.conf."
fi

# Check if HTTP connector is enabled in neo4j.conf
if grep -q "^#*dbms.connector.http.enabled=" "$NEO4J_CONF"; then
    # If the line is present, uncomment it
    sed -i "s/^#*dbms.connector.http.enabled=.*/dbms.connector.http.enabled=true/g" "$NEO4J_CONF"
    echo "HTTP connector enabled in neo4j.conf."
else
    # If the line is not present, add it
    echo "dbms.connector.http.enabled=true" >> "$NEO4J_CONF"
    echo "Added dbms.connector.http.enabled to neo4j.conf."
fi

# Check if APOC procedures are already unrestricted in neo4j.conf
if grep -q "dbms.security.procedures.unrestricted=apoc.*" /var/lib/neo4j/conf/neo4j.conf; then
    echo "APOC procedures already unrestricted in neo4j.conf."
else
    # Add unrestricted procedures line to neo4j.conf
    echo 'dbms.security.procedures.unrestricted=apoc.*' >> "$NEO4J_CONF"
    echo "Updated neo4j.conf to allow unrestricted APOC procedures."
fi

# Update listen address settings for Bolt and HTTP connectors
# For Bolt
if grep -q "^dbms.connector.bolt.listen_address="  "$NEO4J_CONF"; then
    sed -i 's/^dbms.connector.bolt.listen_address=.*/dbms.connector.bolt.listen_address=0.0.0.0:7687/g'  "$NEO4J_CONF"
else
    echo "dbms.connector.bolt.listen_address=0.0.0.0:7687" >> "$NEO4J_CONF"
fi
echo "Bolt connector configuration set to allow connections from any IP address."

# For HTTP
if grep -q "^dbms.connector.http.listen_address="  "$NEO4J_CONF"; then
    sed -i 's/^dbms.connector.http.listen_address=.*/dbms.connector.http.listen_address=0.0.0.0:7474/g'  "$NEO4J_CONF"
else
    echo "dbms.connector.http.listen_address=0.0.0.0:7474" >>  "$NEO4J_CONF"
fi
echo "HTTP connector configuration set to allow connections from any IP address."

# Update the new settings replacing the deprecated ones
sed -i 's/^#*dbms.default_listen_address=.*/# Deprecated setting removed/g'  "$NEO4J_CONF"
sed -i 's/^#*dbms.connector.bolt.listen_address=.*/# Deprecated setting removed/g'  "$NEO4J_CONF"

# Add new settings for default listen address
if ! grep -q "^server.default_listen_address="  "$NEO4J_CONF"; then
    echo "server.default_listen_address=0.0.0.0" >> /var/lib/neo4j/conf/neo4j.conf
    echo "Added new default listen address configuration."
fi

# Add new settings for Bolt listen address
if ! grep -q "^server.bolt.listen_address="  "$NEO4J_CONF"; then
    echo "server.bolt.listen_address=0.0.0.0:7687" >> "$NEO4J_CONF"
    echo "Added new Bolt listen address configuration."
fi