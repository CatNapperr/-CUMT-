package com.example.api.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class MediaUploadResponseDto(
    @Json(name = "id") val id: String,
    @Json(name = "imageUrl") val imageUrl: String,
    @Json(name = "contentType") val contentType: String,
    @Json(name = "sizeBytes") val sizeBytes: Long,
    @Json(name = "width") val width: Int?,
    @Json(name = "height") val height: Int?,
    @Json(name = "source") val source: String,
)
