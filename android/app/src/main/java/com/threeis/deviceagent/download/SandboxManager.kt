package com.threeis.deviceagent.download

import android.os.Environment
import com.threeis.deviceagent.util.Logger
import java.io.File

class SandboxManager {
    private val root: File = File(Environment.getExternalStorageDirectory(), "3is")

    fun clear(): Boolean {
        return try {
            root.listFiles()?.forEach { it.deleteRecursively() }
            if (!root.exists()) root.mkdirs()
            true
        } catch (se: SecurityException) {
            Logger.w("clear() SecurityException, isManager=${Environment.isExternalStorageManager()}: ${se.message}")
            throw se
        }
    }

    fun pathFor(attachmentId: String, ext: String): File {
        if (!root.exists()) root.mkdirs()
        return File(root, "$attachmentId.$ext")
    }
}
