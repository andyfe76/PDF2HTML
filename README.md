# PDF2HTML
Convert PDF to HTML with layout and base64 images

### Configure API

Enable Google Drive and Google Docs API, create and export the credentials JSON

https://developers.google.com/workspace/guides/create-credentials

### Run your code

    from convert import convert

    result_html = convert("test.pdf", credentials_path = "credentials.json", token_path = "token.json")

- the script will look for credentials.json and starts the authorization process
- after succesfull authorization, the token.json will store the token for future usage, without authorization
- save the function response as HTML file. It will be self contained, with embedded images