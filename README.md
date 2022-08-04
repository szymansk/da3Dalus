
# User Guide


1. Start up the Flask server by navigating to the source directory and entering the following command in a terminal. The server runs by default on port 5000: 
```
python main_funktion.py 
```

3. Make your request to the REST API by sending a CPACS file (see *REST API Definition* below)
4. The response from the API is a an STL file containing the modelled object

## REST API Documentaion

### POST /wing-upload

This endpoint is used for the modelling of wings, defined in the CPACS format.
The *request body* should contain a single entry named `file` that points to a CPACS file.
The *response* is an STL file with the modelled object.

### POST /fuselage-upload

 This endpoint is used for the modelling of fuselages, defined in the CPACS format.
The *request body* should contain a single entry named `file` that points to a CPACS file.
The *response* is an STL file with the modelled object.

### Example

![Example in Postman](Postman.png)

*Note: The response in Postman is shown as raw data. The file can be saved by clicking 'Save Response' -> 'Save to a file'.*