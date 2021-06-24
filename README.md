# Drop Token RESTAPI back-end implementation

1. Login to AWS and Navigate to the "CloudFormation" service via links: "Services"->"CloudFormation"
2. Click link "Create stack"->"With new resources"
3. Under 'Specify template' section, select 'Upload a template file' and select the file in this repo: ```infrastructure/master.yml```
4. Click "Next"
5. Input valid parameter values (or keep defaults and move on)
6. Click "Next"
7. Click "Next" again
8. Click "Create stack" and visually confirm that your stack is in the status **CREATE_COMPLETE** 
9. Check the outputs tab for the BASE URL of the API
10. Invoke endpoints using postman/curl/etc (just can't be a CORS service)