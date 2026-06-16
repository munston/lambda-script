-- generated-by: gofur codegen 0.1
module Main where

import System.Environment
import qualified LambdaScript

main :: IO ()
main = getArgs >>= dispatch . normalizeArgs

normalizeArgs :: [String] -> [String]
normalizeArgs [single] = words single
normalizeArgs args = args

dispatch :: [String] -> IO ()
dispatch (option : args) = LambdaScript.go option args >>= print >> return ()
dispatch [] = fail "missing gofur option"
