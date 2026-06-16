module LambdaScript.Core.Check where

import qualified Data.Map.Strict as Map
import qualified Data.Set as Set

import LambdaScript.Core.Ast
import LambdaScript.Core.Diagnostic
import LambdaScript.Core.Program

data Scope = Scope
  { scopeTopLevel :: Set.Set String
  , scopeLocals :: Map.Map String ForeignPrimitiveType
  , scopeSignatures :: Map.Map String FunctionSignature
  , scopeValues :: Map.Map String ForeignPrimitiveType
  }

checkProgram :: Program -> [Diagnostic]
checkProgram program = concatMap checkModule (programModules program)

checkModule :: Module -> [Diagnostic]
checkModule mod =
  let items = moduleDeclarations mod
      dupDiags =
        [ Diagnostic ("Duplicate top-level name: " ++ n)
        | n <- nubByOrder (map topLevelName items)
        , length (filter ((== n) . topLevelName) items) > 1
        ]
      foreignDiags =
        [ Diagnostic ("void cannot be a parameter type for " ++ identifierName (foreignName f))
        | TopForeign f <- items
        , elem TyVoid (foreignParams (foreignSignature f))
        ]
      signatures = foldl registerSignature Map.empty items
      topNames = Set.fromList (map topLevelName items)
      valueDiags = concatMap (checkTopLevel topNames signatures) items
  in dupDiags ++ foreignDiags ++ valueDiags

nubByOrder :: Eq a => [a] -> [a]
nubByOrder = foldr (\x acc -> if x `elem` acc then acc else x : acc) []

registerSignature :: Map.Map String FunctionSignature -> TopLevel -> Map.Map String FunctionSignature
registerSignature sigs item = case item of
  TopFunction fn -> Map.insert (identifierName (functionName fn)) (functionSignature fn) sigs
  TopForeign f ->
    Map.insert
      (identifierName (foreignName f))
      (FunctionSignature (foreignParams (foreignSignature f)) (foreignResult (foreignSignature f)))
      sigs
  _ -> sigs

checkTopLevel :: Set.Set String -> Map.Map String FunctionSignature -> TopLevel -> [Diagnostic]
checkTopLevel topNames signatures item =
  let scope = Scope topNames Map.empty signatures Map.empty
  in case item of
    TopFunction fn -> checkFunction fn scope
    TopDeclaration decl ->
      case inferExpression (declarationValue decl) scope of
        Nothing -> []
        Just _ -> []
    TopForeign _ -> []

checkFunction :: FunctionDeclaration -> Scope -> [Diagnostic]
checkFunction fn scope =
  let localTypes = Map.fromList (zip (map identifierName (functionBoundParams fn)) (functionParams (functionSignature fn)))
      innerScope = scope { scopeLocals = localTypes }
      bodyType = inferExpression (functionBody fn) innerScope
  in case bodyType of
    Nothing -> []
    Just t ->
      if typeCompatible t (functionResult (functionSignature fn))
        then []
        else
          [ Diagnostic
              ( "Function "
                  ++ identifierName (functionName fn)
                  ++ " returns "
                  ++ showType t
                  ++ ", expected "
                  ++ showType (functionResult (functionSignature fn))
              )
          ]

inferExpression :: Expression -> Scope -> Maybe ForeignPrimitiveType
inferExpression expr scope = case expr of
  ExprLiteral lit -> Just (inferLiteral (literalValue lit))
  ExprIdentifier ident ->
    let name = identifierName ident
    in case Map.lookup name (scopeLocals scope) of
      Just t -> Just t
      Nothing -> Map.lookup name (scopeValues scope)
  ExprCall call -> inferCall call scope
  ExprBinary bin ->
    inferBinary
      (binaryOperator bin)
      (inferExpression (binaryLeft bin) scope)
      (inferExpression (binaryRight bin) scope)
  ExprIf ife ->
    let t1 = inferExpression (ifThenBranch ife) scope
        t2 = inferExpression (ifElseBranch ife) scope
    in case (t1, t2) of
      (Just a, Just b) ->
        if typeCompatible a b || typeCompatible b a
          then Just (if a == TyF64 || b == TyF64 then TyF64 else a)
          else Nothing
      _ -> Nothing
  ExprLet letE ->
    let valueType = inferExpression (letValue letE) scope
        inner =
          scope
            { scopeLocals =
                case valueType of
                  Nothing -> scopeLocals scope
                  Just t -> Map.insert (identifierName (letName letE)) t (scopeLocals scope)
            }
    in inferExpression (letBody letE) inner

inferCall :: CallExpression -> Scope -> Maybe ForeignPrimitiveType
inferCall call scope =
  let callee = identifierName (callCallee call)
  in case Map.lookup callee (scopeSignatures scope) of
    Nothing -> Nothing
    Just sig ->
      if length (callArguments call) == length (functionParams sig)
        then Just (functionResult sig)
        else Nothing

inferLiteral :: LiteralValue -> ForeignPrimitiveType
inferLiteral value = case value of
  LitBool _ -> TyBool
  LitString _ -> TyString
  LitInt _ -> TyI32
  LitDouble _ -> TyF64

inferBinary :: String -> Maybe ForeignPrimitiveType -> Maybe ForeignPrimitiveType -> Maybe ForeignPrimitiveType
inferBinary op left right =
  case (left, right) of
    (Just l, Just r) ->
      if op `elem` ["+", "-", "*", "/"]
        then if isNumeric l && isNumeric r then Just (if l == TyF64 || r == TyF64 then TyF64 else TyI32) else Nothing
        else
          if op `elem` ["<", ">", "<=", ">="]
            then if isNumeric l && isNumeric r then Just TyBool else Nothing
            else if op `elem` ["==", "!="]
              then if typeCompatible l r || typeCompatible r l then Just TyBool else Nothing
              else Nothing
    _ -> Nothing

typeCompatible :: ForeignPrimitiveType -> ForeignPrimitiveType -> Bool
typeCompatible actual expected = actual == expected || (actual == TyI32 && expected == TyF64)

isNumeric :: ForeignPrimitiveType -> Bool
isNumeric t = t == TyI32 || t == TyF64

showType :: ForeignPrimitiveType -> String
showType t = case t of
  TyI32 -> "i32"
  TyF64 -> "f64"
  TyBool -> "bool"
  TyString -> "string"
  TyVoid -> "void"