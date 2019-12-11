import * as chai from 'chai';
import { Context } from 'aws-lambda';
import { helloWorld } from './handler';

const expect = chai.expect;
const should = chai.should();

describe("handler", () => {
  describe("hello", () => {
    it("should return Serverless boilerplate message", () => {
        let mockContext = {} as Context;
        helloWorld(null, mockContext, (error : Error, result : any) => {
          expect(error).to.be.null;
          result.body.should.equal('{"message":"Go Serverless v1.0! Your function executed successfully!","input":null}');
      })
    });
  });
});
