package com.threeis.deviceagent.data

data class UrlInfo(
    val attachmentId: String,
    val url: String,
    val md5: String,
    val ext: String = "bin",
)

data class DownloadInstruction(
    val transactionId: String,
    val urls: List<UrlInfo>,
)

data class DownloadResult(
    val attachmentId: String,
    val localPath: String,
    val success: Boolean,
    val errorReason: String? = null,
)
