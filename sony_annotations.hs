{-
    Script for import annotations from one Sony PRS-T1 reader to another with
    some books. Uses Sony_Reader1/database/books.db for source and destionation.
-}

import Control.Exception
import Control.Monad
import Data.Function
import Data.Functor
import Data.List
import qualified Data.Map as M
import Database.HDBC
import Database.HDBC.Sqlite3
import System.Environment
import System.Exit
import System.IO

main = do
    args <- getArgs
    case args of
        [src, dst] -> do
            (aBooks, aAnnotations) <- withDB src
                (\conn -> liftM2 (,) (getBooks conn) (getAnnotations conn))
            withDB dst (\conn -> do
                bBooks <- getBooks conn
                let relation = relateBooks aBooks bBooks
                let update = makePatch aAnnotations relation
                insertAnnotations conn update)
        _ -> printHelp

printHelp = putStrLn "Usage: ./<script> <src_db> <dest_db>"

withDB file = bracket (connectSqlite3 file) disconnect

getBooks conn = quickQuery' conn "SELECT _id, title FROM books;" []

getAnnotations conn = quickQuery' conn "SELECT * FROM annotation;" []

relateBooks a b =
    let a' = sort' $ map toPlain a
        b' = sort' $ map toPlain b
    in M.fromList $ relateBooks' a' b'
    where toPlain [id, title] = (fromSql id, fromSql title)::(Int, String)
          sort' = sortBy (compare `on` snd)

relateBooks' (a:as) (b:bs)
    | (title a) == (title b) = (id a, id b):(relateBooks' as bs)
    | (title a) < (title b) = relateBooks' as (b:bs)
    | (title a) > (title b) = relateBooks' (a:as) bs
    where id = fst
          title = snd

relateBooks' _ _ = []

makePatch as dict = map (updateRow dict) as

updateRow dict (_id:(cid:row)) =
    (toSql newCid) : row
    where oldCid = (fromSql cid)::Int
          newCid = dict M.! oldCid

insertAnnotations conn update  = do
    mapM_ (insertAnnotation conn) update
    commit conn

insertAnnotation conn values =
    run conn "INSERT INTO annotation (content_id, markup_type, added_date, modified_date, name, marked_text, mark, mark_end, page, total_page, mime_type, file_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);" values

