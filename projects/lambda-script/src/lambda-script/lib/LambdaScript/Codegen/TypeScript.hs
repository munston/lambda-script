module LambdaScript.Codegen.TypeScript where

import Data.List
import qualified Data.Set as Set

import LambdaScript.Core.Ast
import LambdaScript.Core.Program

emitTypeScript :: Program -> String
emitTypeScript program =
  let hasFFI = any moduleHasForeign (programModules program)
      header =
        if hasFFI
          then "import { CppForeignRuntime } from '../runtime/cppForeign';\n\n"
          else ""
      body = concatMap emitModule (programModules program)
  in trimEnd (header ++ body)

moduleHasForeign :: Module -> Bool
moduleHasForeign lsModule = any isForeign (moduleDeclarations lsModule)
  where
    isForeign item = case item of
      TopForeign _ -> True
      _ -> False

emitModule :: Module -> String
emitModule lsModule =
  let foreignSet = Set.fromList [identifierName (foreignName f) | TopForeign f <- moduleDeclarations lsModule]
      foreignChunk = concatMap emitForeign (filter isForeignDecl (moduleDeclarations lsModule))
      restChunk = concatMap (emitTopLevel foreignSet) (moduleDeclarations lsModule)
  in "// Module: " ++ moduleName lsModule ++ "\n\n" ++ foreignChunk ++ restChunk
  where
    isForeignDecl item = case item of
      TopForeign _ -> True
      _ -> False

emitForeign :: TopLevel -> String
emitForeign item = case item of
  TopForeign f ->
    let params =
          intercalate ", " $
              zipWith
              (\idx t -> "arg" ++ show (idx :: Int) ++ ": " ++ mapTsType t)
              [0 :: Int ..]
              (foreignParams (foreignSignature f))
        ret = mapTsType (foreignResult (foreignSignature f))
        argNames =
          intercalate ", " $
            zipWith (\idx _ -> "arg" ++ show (idx :: Int)) [0 :: Int ..] (foreignParams (foreignSignature f))
    in unlines
         [ "export function " ++ identifierName (foreignName f) ++ "(runtime: CppForeignRuntime, " ++ params ++ "): " ++ ret ++ " {"
         , "  return runtime.call({ symbol: '" ++ foreignSymbol f ++ "', args: [" ++ argNames ++ "] }) as " ++ ret ++ ";"
         , "}"
         , ""
         ]
  _ -> ""

emitTopLevel :: Set.Set String -> TopLevel -> String
emitTopLevel foreignSet item = case item of
  TopForeign _ -> ""
  TopFunction fn -> emitFunction fn
  TopDeclaration decl -> emitDeclaration decl foreignSet

emitFunction :: FunctionDeclaration -> String
emitFunction fn =
  let params =
        intercalate ", " $
          zipWith
            (\p t -> identifierName p ++ ": " ++ mapTsType t)
            (functionBoundParams fn)
            (functionParams (functionSignature fn))
      ret = mapTsType (functionResult (functionSignature fn))
  in unlines
       [ "export function " ++ identifierName (functionName fn) ++ "(" ++ params ++ "): " ++ ret ++ " {"
       , "  return " ++ emitExpr (functionBody fn) ++ ";"
       , "}"
       , ""
       ]

emitDeclaration :: Declaration -> Set.Set String -> String
emitDeclaration decl foreignSet =
  case declarationValue decl of
    ExprCall call | Set.member (identifierName (callCallee call)) foreignSet ->
      let args = intercalate ", " (map emitExpr (callArguments call))
      in unlines
           [ "export function " ++ identifierName (declarationName decl) ++ "(runtime: CppForeignRuntime) {"
           , "  return " ++ identifierName (callCallee call) ++ "(runtime, " ++ args ++ ");"
           , "}"
           , ""
           ]
    value ->
      unlines
        [ "export const " ++ identifierName (declarationName decl) ++ " = " ++ emitExpr value ++ ";"
        , ""
        ]

mapTsType :: ForeignPrimitiveType -> String
mapTsType t = case t of
  TyI32 -> "number"
  TyF64 -> "number"
  TyBool -> "boolean"
  TyString -> "string"
  TyVoid -> "null"

emitExpr :: Expression -> String
emitExpr expr = case expr of
  ExprLiteral lit -> emitLiteral (literalValue lit)
  ExprIdentifier ident -> identifierName ident
  ExprCall call ->
    identifierName (callCallee call)
      ++ "("
      ++ intercalate ", " (map emitExpr (callArguments call))
      ++ ")"
  ExprBinary bin ->
    "(" ++ emitExpr (binaryLeft bin) ++ " " ++ binaryOperator bin ++ " " ++ emitExpr (binaryRight bin) ++ ")"
  ExprIf ife ->
    "("
      ++ emitExpr (ifCondition ife)
      ++ " ? "
      ++ emitExpr (ifThenBranch ife)
      ++ " : "
      ++ emitExpr (ifElseBranch ife)
      ++ ")"
  ExprLet letE ->
    "(() => { const "
      ++ identifierName (letName letE)
      ++ " = "
      ++ emitExpr (letValue letE)
      ++ "; return "
      ++ emitExpr (letBody letE)
      ++ "; })()"

emitLiteral :: LiteralValue -> String
emitLiteral value = case value of
  LitBool b -> if b then "true" else "false"
  LitString s -> show s
  LitInt n -> show n
  LitDouble n -> show n

trimEnd :: String -> String
trimEnd = reverse . dropWhile (== '\n') . reverse . dropWhile (== ' ')