import { Handler, Callback, Context } from 'aws-lambda';
import 'source-map-support/register';

export let helloWorld : Handler = (event, context : Context, callback : Callback) => {
  const response = {
    statusCode: 200,
    headers: {
      'Access-Control-Allow-Origin': '*', // Required for CORS support to work
    },
    body: JSON.stringify({
      message: 'Go Serverless v1.0! Your function executed successfully!',
      input: event,
    }),
  };

  callback(null, response);
};
