module LambdaScript.Core.Program where

import LambdaScript.Core.Ast

data Module = Module
  { moduleName :: String
  , moduleDeclarations :: [TopLevel]
  } deriving (Eq, Show, Read)

data Program = Program
  { programModules :: [Module]
  } deriving (Eq, Show, Read)