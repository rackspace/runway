import { handler } from "./helloWorld";

import {
  APIGatewayProxyEvent,
  APIGatewayProxyResult,
  Context,
} from "aws-lambda";

describe("Test handler", () => {
  test("Verify Serverless boilerplate message is returned", async () => {
    function unusedCallback<T>() {
      return (undefined as any) as T;
    }

    const data = await handler(
      {} as APIGatewayProxyEvent,
      {} as Context,
      unusedCallback<any>(),
    );
    expect((data as APIGatewayProxyResult).statusCode).toBe(200);
    expect((data as APIGatewayProxyResult).body).toBe(
      '{"message":"Go Serverless v1.0! Your function executed successfully!","input":{}}',
    );
  });
});
