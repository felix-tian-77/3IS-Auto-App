package com.threeis.deviceagent.download

import com.threeis.deviceagent.data.DownloadResult
import com.threeis.deviceagent.data.DownloadInstruction
import com.threeis.deviceagent.data.UrlInfo
import com.threeis.deviceagent.util.Logger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

class Downloader(private val sandbox: SandboxManager) {

    private val http = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    suspend fun downloadAll(instr: DownloadInstruction): List<DownloadResult> =
        withContext(Dispatchers.IO) {
            val results = mutableListOf<DownloadResult>()
            for ((index, info) in instr.urls.withIndex()) {
                onProgress(index + 1, instr.urls.size, info.attachmentId)
                val r = downloadOne(info)
                results += r
                if (!r.success) {
                    instr.urls.drop(index + 1).forEach {
                        results += DownloadResult(it.attachmentId, "", false, "SKIPPED_PRIOR_FAIL")
                    }
                    return@withContext results
                }
            }
            results
        }

    private fun onProgress(current: Int, total: Int, attachmentId: String) {
        // Listener wired in T14 via Service
        Logger.d("download progress $current/$total $attachmentId")
    }

    private fun downloadOne(info: UrlInfo): DownloadResult {
        val target = sandbox.pathFor(info.attachmentId, info.ext)
        val tmp = File(target.parentFile, "${info.attachmentId}.${info.ext}.part")
        return try {
            attemptDownload(info, target, tmp)
        } catch (io: java.io.IOException) {
            // Retry once on transient network error (spec §4.4)
            tmp.delete()
            try {
                kotlinx.coroutines.runBlocking { kotlinx.coroutines.delay(1000) }
                attemptDownload(info, target, tmp)
            } catch (io2: java.io.IOException) {
                tmp.delete()
                DownloadResult(info.attachmentId, target.absolutePath, false, "NETWORK_ERROR")
            } catch (ce: kotlinx.coroutines.CancellationException) {
                tmp.delete()
                throw ce
            } catch (sec: SecurityException) {
                tmp.delete()
                DownloadResult(info.attachmentId, target.absolutePath, false, "IO_ERROR")
            }
        } catch (ce: kotlinx.coroutines.CancellationException) {
            tmp.delete()
            throw ce
        } catch (sec: SecurityException) {
            tmp.delete()
            DownloadResult(info.attachmentId, target.absolutePath, false, "IO_ERROR")
        }
    }

    private fun attemptDownload(info: UrlInfo, target: File, tmp: File): DownloadResult {
        val req = Request.Builder().url(info.url).build()
        http.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) {
                val reason = if (resp.code == 403 || resp.code == 410) "URL_EXPIRED" else "NETWORK_ERROR"
                return DownloadResult(info.attachmentId, target.absolutePath, false, reason)
            }
            val body = resp.body ?: return DownloadResult(info.attachmentId, target.absolutePath, false, "IO_ERROR")
            tmp.outputStream().use { out ->
                body.byteStream().copyTo(out)
            }
            val md5 = md5Of(tmp)
            if (!md5.equals(info.md5, ignoreCase = true)) {
                tmp.delete()
                return DownloadResult(info.attachmentId, target.absolutePath, false, "MD5_MISMATCH")
            }
            if (target.exists()) target.delete()
            if (!tmp.renameTo(target)) {
                return DownloadResult(info.attachmentId, target.absolutePath, false, "IO_ERROR")
            }
            return DownloadResult(info.attachmentId, target.absolutePath, true)
        }
    }

    private fun md5Of(f: File): String {
        val digest = MessageDigest.getInstance("MD5")
        f.inputStream().use { input ->
            val buf = ByteArray(8192)
            while (true) {
                val n = input.read(buf)
                if (n <= 0) break
                digest.update(buf, 0, n)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
