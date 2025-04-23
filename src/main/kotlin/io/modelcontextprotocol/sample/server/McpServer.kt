package io.modelcontextprotocol.sample.server

import io.ktor.client.*
import io.ktor.client.plugins.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.request.*
import io.ktor.client.statement.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import io.ktor.utils.io.streams.*
import io.modelcontextprotocol.kotlin.sdk.*
import io.modelcontextprotocol.kotlin.sdk.server.Server
import io.modelcontextprotocol.kotlin.sdk.server.ServerOptions
import io.modelcontextprotocol.kotlin.sdk.server.StdioServerTransport
import kotlinx.coroutines.Job
import kotlinx.coroutines.runBlocking
import kotlinx.io.asSink
import kotlinx.io.buffered
import kotlinx.serialization.json.*

// Extension functions to work with the API
suspend fun HttpClient.listPurchases(email: String? = null): String {
    val response = get("/api/listPurchases") {
        if (email != null) {
            parameter("email", email)
        }
    }
    return response.bodyAsText()
}

suspend fun HttpClient.requestRefund(purchaseId: String, reason: String): String {
    val response = post("/api/requestRefund") {
        contentType(ContentType.Application.Json)
        setBody(buildJsonObject {
            put("purchase_id", purchaseId)
            put("reason", reason)
        }.toString())
    }
    return response.bodyAsText()
}

suspend fun HttpClient.sendRefundCompleteEmail(refundId: String, email: String? = null): String {
    val requestBody = buildJsonObject {
        put("refund_id", refundId)
        if (email != null) {
            put("email", email)
        }
    }

    val response = post("/api/sendRefundCompleteEmail") {
        contentType(ContentType.Application.Json)
        setBody(requestBody.toString())
    }
    return response.bodyAsText()
}

// Main function to run the MCP server
fun `run mcp server`() {
    // Base URL for the Refund API
    val baseUrl = "http://localhost:5000/"

    // Create an HTTP client with a default request configuration and JSON content negotiation
    val httpClient = HttpClient {
        defaultRequest {
            url(baseUrl)
            contentType(ContentType.Application.Json)
        }
        // Install content negotiation plugin for JSON serialization/deserialization
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                prettyPrint = true
            })
        }
    }

    // Create the MCP Server instance with a basic implementation
    val server = Server(
        Implementation(
            name = "refundpy", // Tool name is "refundpy"
            version = "1.0.0" // Version of the implementation
        ),
        ServerOptions(
            capabilities = ServerCapabilities(tools = ServerCapabilities.Tools(listChanged = true))
        )
    )

    // Register a tool to fetch purchases
    server.addTool(
        name = "list_purchases",
        description = """
            List purchases that have been made (Read only)
        """.trimIndent(),
        inputSchema = Tool.Input(
            properties = buildJsonObject {
                putJsonObject("email") {
                    put("type", "string")
                    put("description", "Required so we don't access someone else's purchases")
                }
            },
            required = listOf("email")
        )
    ) { request ->
        val email = request.arguments["email"]?.jsonPrimitive?.contentOrNull
        val response = httpClient.listPurchases(email)
        CallToolResult(content = listOf(TextContent(response)))
    }

    // Register a tool to request refund
    server.addTool(
        name = "request_refund",
        description = """
            Request refund for a purchase
        """.trimIndent(),
        inputSchema = Tool.Input(
            properties = buildJsonObject {
                putJsonObject("purchase_id") {  // Changed from refund_id to purchase_id
                    put("type", "string")
                    put("description", "ID of the purchase to refund")
                }
                putJsonObject("reason") {
                    put("type", "string")
                    put("description", "Reason for requesting the refund")
                }
            },
            required = listOf("purchase_id", "reason")  // Changed from refund_id to purchase_id
        )
    ) { request ->
        val purchaseId = request.arguments["purchase_id"]?.jsonPrimitive?.contentOrNull  // Changed from refund_id
        val reason = request.arguments["reason"]?.jsonPrimitive?.contentOrNull
        if (purchaseId == null || reason == null) {
            return@addTool CallToolResult(
                content = listOf(TextContent("The 'purchase_id' and 'reason' parameters are required."))
            )
        }
        val response = httpClient.requestRefund(purchaseId, reason)
        CallToolResult(content = listOf(TextContent(response)))
    }

    server.addTool(
        name = "send_refund_complete_email",
        description = """
            Send refund complete email
        """.trimIndent(),
        inputSchema = Tool.Input(
            properties = buildJsonObject {
                putJsonObject("refund_id") {
                    put("type", "string")
                    put("description", "ID of the refund to complete")
                }
                putJsonObject("email") {
                    put("type", "string")
                    put("description", "Optional override email to send the notification to")
                }
            },
            required = listOf("refund_id")
        )
    ) { request ->
        val refundId = request.arguments["refund_id"]?.jsonPrimitive?.contentOrNull
        val email = request.arguments["email"]?.jsonPrimitive?.contentOrNull
        if (refundId == null) {
            return@addTool CallToolResult(
                content = listOf(TextContent("The 'refund_id' is required."))
            )
        }
        val response = httpClient.sendRefundCompleteEmail(refundId, email)
        CallToolResult(content = listOf(TextContent(response)))
    }

    // Create a transport using standard IO for server communication
    val transport = StdioServerTransport(
        System.`in`.asInput(),
        System.out.asSink().buffered()
    )

    runBlocking {
        server.connect(transport)
        val done = Job()
        server.onClose {
            done.complete()
        }
        done.join()
    }
}
