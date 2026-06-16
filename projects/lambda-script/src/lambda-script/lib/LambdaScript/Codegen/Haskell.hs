module LambdaScript.Codegen.Haskell where

import Data.List
import qualified Data.Set as Set

import LambdaScript.Core.Ast
import LambdaScript.Core.Program

emitHaskell :: Program -> String
emitHaskell program =
  let chunks = concatMap emitModule (programModules program)
      body = unlines chunks
      needsCString = any moduleNeedsCString (programModules program)
  in trimEnd $
       if needsCString
         then "import Foreign.C.String (CString, withCString)\n\n" ++ body
         else body

moduleNeedsCString :: Module -> Bool
moduleNeedsCString lsModule =
  any foreignUsesCString (moduleDeclarations lsModule)
    || any declarationNeedsCString (moduleDeclarations lsModule)
  where
    foreignUsesCString item = case item of
      TopForeign f ->
        TyString `elem` foreignParams (foreignSignature f)
          || foreignResult (foreignSignature f) == TyString
      _ -> False

    declarationNeedsCString item = case item of
      TopDeclaration decl ->
        case declarationValue decl of
          ExprCall call ->
            case findForeign (identifierName (callCallee call)) of
              Just ffi ->
                TyString `elem` foreignParams (foreignSignature ffi)
                  && any isStringLiteralExpr (callArguments call)
              Nothing -> False
          _ -> False
      _ -> False

    findForeign name =
      let matches =
            [ f
            | TopForeign f <- moduleDeclarations lsModule
            , identifierName (foreignName f) == name
            ]
      in case matches of
        ffi : _ -> Just ffi
        [] -> Nothing

emitModule :: Module -> [String]
emitModule lsModule =
  let foreignSet = Set.fromList [identifierName (foreignName f) | TopForeign f <- moduleDeclarations lsModule]
  in ("-- Module: " ++ moduleName lsModule) : "" : concatMap (emitTopLevel lsModule foreignSet) (moduleDeclarations lsModule)

emitTopLevel :: Module -> Set.Set String -> TopLevel -> [String]
emitTopLevel lsModule foreignSet item = case item of
  TopForeign f -> emitForeign f
  TopFunction fn -> emitFunction fn
  TopDeclaration decl -> emitDeclaration lsModule foreignSet decl

emitForeign :: ForeignImport -> [String]
emitForeign f =
  let params = intercalate " -> " (map mapHaskellType (foreignParams (foreignSignature f)))
      ret = mapHaskellType (foreignResult (foreignSignature f))
  in [ "foreign import ccall \"" ++ foreignSymbol f ++ "\" " ++ identifierName (foreignName f) ++ " :: " ++ params ++ " -> IO " ++ ret, "" ]

emitFunction :: FunctionDeclaration -> [String]
emitFunction fn =
  let params = map mapHaskellType (functionParams (functionSignature fn))
      sig = intercalate " -> " (params ++ [mapHaskellType (functionResult (functionSignature fn))])
      argNames = intercalate " " (map identifierName (functionBoundParams fn))
  in
    [ identifierName (functionName fn) ++ " :: " ++ sig
    , identifierName (functionName fn) ++ " " ++ argNames ++ " = " ++ emitExpr (functionBody fn)
    , ""
    ]

emitDeclaration :: Module -> Set.Set String -> Declaration -> [String]
emitDeclaration lsModule foreignSet decl =
  case declarationValue decl of
    ExprCall call | Set.member (identifierName (callCallee call)) foreignSet ->
      let ffi = findForeignInModule lsModule (identifierName (callCallee call))
          retType = maybe "Int" (mapHaskellType . foreignResult . foreignSignature) ffi
          body =
            case ffi of
              Just f
                | TyString `elem` foreignParams (foreignSignature f)
                  , arg : _ <- callArguments call
                  , isStringLiteralExpr arg ->
                  identifierName (declarationName decl)
                    ++ " = withCString "
                    ++ emitLiteralString arg
                    ++ " "
                    ++ identifierName (callCallee call)
              _ ->
                let args = intercalate " " (map emitExpr (callArguments call))
                in identifierName (declarationName decl) ++ " = " ++ identifierName (callCallee call) ++ (if null args then "" else " " ++ args)
      in [ identifierName (declarationName decl) ++ " :: IO " ++ retType, body, "" ]
    value ->
      [ identifierName (declarationName decl) ++ " = " ++ emitExpr value, "" ]

findForeignInModule :: Module -> String -> Maybe ForeignImport
findForeignInModule lsModule name =
  let matches =
        [ f
        | TopForeign f <- moduleDeclarations lsModule
        , identifierName (foreignName f) == name
        ]
  in case matches of
    ffi : _ -> Just ffi
    [] -> Nothing

isStringLiteralExpr :: Expression -> Bool
isStringLiteralExpr expr = case expr of
  ExprLiteral lit -> case literalValue lit of
    LitString _ -> True
    _ -> False
  _ -> False

emitLiteralString :: Expression -> String
emitLiteralString expr = case expr of
  ExprLiteral lit -> case literalValue lit of
    LitString s -> show s
    _ -> "/* unsupported */"
  _ -> "/* unsupported */"

mapHaskellType :: ForeignPrimitiveType -> String
mapHaskellType t = case t of
  TyI32 -> "Int"
  TyF64 -> "Double"
  TyBool -> "Bool"
  TyString -> "CString"
  TyVoid -> "()"

emitExpr :: Expression -> String
emitExpr expr = case expr of
  ExprLiteral lit -> emitLiteral (literalValue lit)
  ExprIdentifier ident -> identifierName ident
  ExprCall call ->
    let args = map emitCallArg (callArguments call)
        spaced = intercalate " " args
    in if null spaced then identifierName (callCallee call) else identifierName (callCallee call) ++ " " ++ spaced
  ExprBinary bin ->
    "(" ++ emitExpr (binaryLeft bin) ++ " " ++ binaryOperator bin ++ " " ++ emitExpr (binaryRight bin) ++ ")"
  ExprIf ife ->
    "(if " ++ emitExpr (ifCondition ife) ++ " then " ++ emitExpr (ifThenBranch ife) ++ " else " ++ emitExpr (ifElseBranch ife) ++ ")"
  ExprLet letE ->
    "(let " ++ identifierName (letName letE) ++ " = " ++ emitExpr (letValue letE) ++ " in " ++ emitExpr (letBody letE) ++ ")"

emitCallArg :: Expression -> String
emitCallArg arg =
  let emitted = emitExpr arg
  in case arg of
    ExprLiteral _ -> emitted
    ExprIdentifier _ -> emitted
    _ -> parenIfNeeded emitted

emitLiteral :: LiteralValue -> String
emitLiteral value = case value of
  LitBool True -> "True"
  LitBool False -> "False"
  LitString s -> show s
  LitInt n -> show n
  LitDouble n -> show n

parenIfNeeded :: String -> String
parenIfNeeded s =
  if not (null s) && head s == '(' && last s == ')' then s else "(" ++ s ++ ")"

trimEnd :: String -> String
trimEnd = reverse . dropWhile (== '\n') . reverse . dropWhile (== ' ')