using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Net.Http;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using ImageDescriber.Full.Models;
using Microsoft.Extensions.Logging;

namespace ImageDescriber.Full.Services
{
    public interface IAIProvider
    {
        string Name { get; }
        string DisplayName { get; }
        bool IsConfigured { get; }
        Task<List<string>> GetAvailableModelsAsync();
        Task<string> GenerateDescriptionAsync(string imagePath, string model, string prompt);
        void Configure(Dictionary<string, string> settings);
    }

    public class OpenAIProvider : IAIProvider
    {
        private readonly HttpClient _httpClient;
        private readonly ILogger<OpenAIProvider> _logger;
        private string? _apiKey;

        public string Name => "openai";
        public string DisplayName => "OpenAI";
        public bool IsConfigured => !string.IsNullOrEmpty(_apiKey);

        public OpenAIProvider(HttpClient httpClient, ILogger<OpenAIProvider> logger)
        {
            _httpClient = httpClient;
            _logger = logger;
        }

        public void Configure(Dictionary<string, string> settings)
        {
            settings.TryGetValue("api_key", out _apiKey);
        }

        public async Task<List<string>> GetAvailableModelsAsync()
        {
            if (!IsConfigured)
            {
                _logger.LogWarning("OpenAI provider not configured");
                return new List<string> { "gpt-4-vision-preview (Not Configured)" };
            }

            try
            {
                _httpClient.DefaultRequestHeaders.Authorization = 
                    new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", _apiKey);

                var response = await _httpClient.GetAsync("https://api.openai.com/v1/models");
                if (response.IsSuccessStatusCode)
                {
                    var content = await response.Content.ReadAsStringAsync();
                    var data = JsonConvert.DeserializeObject<JObject>(content);
                    var models = new List<string>();

                    if (data?["data"] is JArray modelsArray)
                    {
                        foreach (var model in modelsArray)
                        {
                            var modelId = model["id"]?.ToString();
                            if (!string.IsNullOrEmpty(modelId) && 
                                (modelId.Contains("gpt-4") && modelId.Contains("vision")))
                            {
                                models.Add(modelId);
                            }
                        }
                    }

                    return models.Count > 0 ? models : new List<string> { "gpt-4-vision-preview" };
                }
                else
                {
                    _logger.LogError("Failed to fetch OpenAI models: {StatusCode}", response.StatusCode);
                    return new List<string> { "gpt-4-vision-preview (Error fetching models)" };
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error fetching OpenAI models");
                return new List<string> { "gpt-4-vision-preview (Connection Error)" };
            }
        }

        public async Task<string> GenerateDescriptionAsync(string imagePath, string model, string prompt)
        {
            if (!IsConfigured)
            {
                throw new InvalidOperationException("OpenAI provider not configured");
            }

            try
            {
                var imageBytes = await System.IO.File.ReadAllBytesAsync(imagePath);
                var base64Image = Convert.ToBase64String(imageBytes);
                var mimeType = GetMimeType(imagePath);

                var requestBody = new
                {
                    model = model,
                    messages = new[]
                    {
                        new
                        {
                            role = "user",
                            content = new[]
                            {
                                new { type = "text", text = prompt },
                                new { type = "image_url", image_url = new { url = $"data:{mimeType};base64,{base64Image}" } }
                            }
                        }
                    },
                    max_tokens = 1000
                };

                _httpClient.DefaultRequestHeaders.Authorization = 
                    new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", _apiKey);

                var json = JsonConvert.SerializeObject(requestBody);
                var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync("https://api.openai.com/v1/chat/completions", content);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseContent = await response.Content.ReadAsStringAsync();
                    var responseData = JsonConvert.DeserializeObject<JObject>(responseContent);
                    return responseData?["choices"]?[0]?["message"]?["content"]?.ToString() ?? "No description generated";
                }
                else
                {
                    var errorContent = await response.Content.ReadAsStringAsync();
                    throw new Exception($"OpenAI API error: {response.StatusCode} - {errorContent}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error generating description with OpenAI");
                throw;
            }
        }

        private string GetMimeType(string imagePath)
        {
            var extension = System.IO.Path.GetExtension(imagePath).ToLower();
            return extension switch
            {
                ".jpg" or ".jpeg" => "image/jpeg",
                ".png" => "image/png",
                ".gif" => "image/gif",
                ".webp" => "image/webp",
                _ => "image/jpeg"
            };
        }
    }

    public class OllamaProvider : IAIProvider
    {
        private readonly HttpClient _httpClient;
        private readonly ILogger<OllamaProvider> _logger;
        private string _baseUrl = "http://localhost:11434";

        public string Name => "ollama";
        public string DisplayName => "Ollama (Local)";
        public bool IsConfigured => true; // Ollama doesn't require API key

        public OllamaProvider(HttpClient httpClient, ILogger<OllamaProvider> logger)
        {
            _httpClient = httpClient;
            _logger = logger;
        }

        public void Configure(Dictionary<string, string> settings)
        {
            if (settings.TryGetValue("base_url", out var baseUrl))
            {
                _baseUrl = baseUrl;
            }
        }

        public async Task<List<string>> GetAvailableModelsAsync()
        {
            try
            {
                var response = await _httpClient.GetAsync($"{_baseUrl}/api/tags");
                if (response.IsSuccessStatusCode)
                {
                    var content = await response.Content.ReadAsStringAsync();
                    var data = JsonConvert.DeserializeObject<JObject>(content);
                    var models = new List<string>();

                    if (data?["models"] is JArray modelsArray)
                    {
                        foreach (var model in modelsArray)
                        {
                            var modelName = model["name"]?.ToString();
                            if (!string.IsNullOrEmpty(modelName))
                            {
                                // Filter out cloud models (ending with -cloud) for local provider
                                if (!modelName.EndsWith("-cloud", StringComparison.OrdinalIgnoreCase))
                                {
                                    models.Add(modelName);
                                }
                            }
                        }
                    }

                    return models.Count > 0 ? models : new List<string> { "llava:7b (No local models installed)" };
                }
                else
                {
                    _logger.LogWarning("Ollama not available: {StatusCode}", response.StatusCode);
                    return new List<string> { "llava:7b (Ollama not running)" };
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error connecting to Ollama");
                return new List<string> { "llava:7b (Connection Error)" };
            }
        }

        public async Task<string> GenerateDescriptionAsync(string imagePath, string model, string prompt)
        {
            try
            {
                var imageBytes = await System.IO.File.ReadAllBytesAsync(imagePath);
                var base64Image = Convert.ToBase64String(imageBytes);

                var requestBody = new
                {
                    model = model,
                    prompt = prompt,
                    images = new[] { base64Image },
                    stream = false
                };

                var json = JsonConvert.SerializeObject(requestBody);
                var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync($"{_baseUrl}/api/generate", content);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseContent = await response.Content.ReadAsStringAsync();
                    var responseData = JsonConvert.DeserializeObject<JObject>(responseContent);
                    return responseData?["response"]?.ToString() ?? "No description generated";
                }
                else
                {
                    var errorContent = await response.Content.ReadAsStringAsync();
                    throw new Exception($"Ollama API error: {response.StatusCode} - {errorContent}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error generating description with Ollama");
                throw;
            }
        }
    }

    public class OllamaCloudProvider : IAIProvider
    {
        private readonly HttpClient _httpClient;
        private readonly ILogger<OllamaCloudProvider> _logger;
        private string _baseUrl = "http://localhost:11434";
        
        // Known cloud models based on Python implementation
        private readonly List<string> _cloudModels = new()
        {
            "qwen3-coder:480b-cloud",
            "gpt-oss:120b-cloud", 
            "gpt-oss:20b-cloud",
            "deepseek-v3.1:671b-cloud"
        };

        public string Name => "ollama_cloud";
        public string DisplayName => "Ollama Cloud";
        public bool IsConfigured => true; // Cloud models don't require separate API key

        public OllamaCloudProvider(HttpClient httpClient, ILogger<OllamaCloudProvider> logger)
        {
            _httpClient = httpClient;
            _logger = logger;
        }

        public void Configure(Dictionary<string, string> settings)
        {
            if (settings.TryGetValue("base_url", out var baseUrl))
            {
                _baseUrl = baseUrl;
            }
        }

        public async Task<List<string>> GetAvailableModelsAsync()
        {
            try
            {
                var response = await _httpClient.GetAsync($"{_baseUrl}/api/tags");
                if (response.IsSuccessStatusCode)
                {
                    var content = await response.Content.ReadAsStringAsync();
                    var data = JsonConvert.DeserializeObject<JObject>(content);
                    var availableCloudModels = new List<string>();

                    if (data?["models"] is JArray modelsArray)
                    {
                        var allModels = modelsArray.Select(m => m["name"]?.ToString()).Where(n => !string.IsNullOrEmpty(n)).ToList();
                        
                        // Filter to only cloud models (ending with -cloud)
                        availableCloudModels = allModels.Where(m => m!.EndsWith("-cloud", StringComparison.OrdinalIgnoreCase)).ToList()!;
                    }

                    return availableCloudModels.Count > 0 ? availableCloudModels : new List<string> { "Cloud models (Not signed in or unavailable)" };
                }
                else
                {
                    _logger.LogWarning("Ollama not available for cloud models: {StatusCode}", response.StatusCode);
                    return new List<string> { "Cloud models (Ollama not running)" };
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error fetching Ollama cloud models");
                return new List<string> { "Cloud models (Connection Error)" };
            }
        }

        public async Task<string> GenerateDescriptionAsync(string imagePath, string model, string prompt)
        {
            try
            {
                var imageBytes = await System.IO.File.ReadAllBytesAsync(imagePath);
                var base64Image = Convert.ToBase64String(imageBytes);

                var requestBody = new
                {
                    model = model,
                    prompt = prompt,
                    images = new[] { base64Image },
                    stream = false
                };

                var json = JsonConvert.SerializeObject(requestBody);
                var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync($"{_baseUrl}/api/generate", content);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseContent = await response.Content.ReadAsStringAsync();
                    var responseData = JsonConvert.DeserializeObject<JObject>(responseContent);
                    return responseData?["response"]?.ToString() ?? "No description generated";
                }
                else
                {
                    var errorContent = await response.Content.ReadAsStringAsync();
                    throw new Exception($"Ollama Cloud API error: {response.StatusCode} - {errorContent}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error generating description with Ollama Cloud");
                throw;
            }
        }
    }

    public class HuggingFaceProvider : IAIProvider
    {
        private readonly HttpClient _httpClient;
        private readonly ILogger<HuggingFaceProvider> _logger;
        private string? _apiKey;

        public string Name => "huggingface";
        public string DisplayName => "Hugging Face";
        public bool IsConfigured => !string.IsNullOrEmpty(_apiKey);

        public HuggingFaceProvider(HttpClient httpClient, ILogger<HuggingFaceProvider> logger)
        {
            _httpClient = httpClient;
            _logger = logger;
        }

        public void Configure(Dictionary<string, string> settings)
        {
            settings.TryGetValue("api_key", out _apiKey);
        }

        public async Task<List<string>> GetAvailableModelsAsync()
        {
            // HuggingFace has many vision models, return a curated list
            var models = new List<string>
            {
                "Salesforce/blip-image-captioning-base",
                "Salesforce/blip-image-captioning-large", 
                "microsoft/git-base-coco",
                "nlpconnect/vit-gpt2-image-captioning"
            };

            if (!IsConfigured)
            {
                return models.ConvertAll(m => m + " (Not Configured)");
            }

            return models;
        }

        public async Task<string> GenerateDescriptionAsync(string imagePath, string model, string prompt)
        {
            if (!IsConfigured)
            {
                throw new InvalidOperationException("HuggingFace provider not configured");
            }

            try
            {
                var imageBytes = await System.IO.File.ReadAllBytesAsync(imagePath);

                _httpClient.DefaultRequestHeaders.Authorization = 
                    new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", _apiKey);

                var content = new ByteArrayContent(imageBytes);
                content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("image/jpeg");

                var response = await _httpClient.PostAsync($"https://api-inference.huggingface.co/models/{model}", content);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseContent = await response.Content.ReadAsStringAsync();
                    var responseData = JsonConvert.DeserializeObject<JArray>(responseContent);
                    
                    if (responseData != null && responseData.Count > 0)
                    {
                        return responseData[0]?["generated_text"]?.ToString() ?? "No description generated";
                    }
                    
                    return "No description generated";
                }
                else
                {
                    var errorContent = await response.Content.ReadAsStringAsync();
                    throw new Exception($"HuggingFace API error: {response.StatusCode} - {errorContent}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error generating description with HuggingFace");
                throw;
            }
        }
    }

    public class AIProviderService
    {
        private readonly Dictionary<string, IAIProvider> _providers;
        private readonly ILogger<AIProviderService> _logger;

        public AIProviderService(IEnumerable<IAIProvider> providers, ILogger<AIProviderService> logger)
        {
            _providers = providers.ToDictionary(p => p.Name, p => p);
            _logger = logger;
        }

        public List<AIProviderInfo> GetAvailableProviders()
        {
            var providerInfos = new List<AIProviderInfo>();
            
            foreach (var provider in _providers.Values)
            {
                providerInfos.Add(new AIProviderInfo(
                    provider.DisplayName,
                    provider.Name,
                    provider.IsConfigured ? "Configured" : "Requires Configuration",
                    provider.IsConfigured
                ));
            }

            return providerInfos;
        }

        public IAIProvider? GetProvider(string name)
        {
            _providers.TryGetValue(name, out var provider);
            return provider;
        }

        public async Task<List<string>> GetAvailableModelsAsync(string providerName)
        {
            var provider = GetProvider(providerName);
            if (provider == null)
            {
                _logger.LogWarning("Provider {ProviderName} not found", providerName);
                return new List<string>();
            }

            return await provider.GetAvailableModelsAsync();
        }

        public async Task<string> GenerateDescriptionAsync(string providerName, string model, string imagePath, string prompt)
        {
            var provider = GetProvider(providerName);
            if (provider == null)
            {
                throw new InvalidOperationException($"Provider {providerName} not found");
            }

            return await provider.GenerateDescriptionAsync(imagePath, model, prompt);
        }

        public void ConfigureProvider(string providerName, Dictionary<string, string> settings)
        {
            var provider = GetProvider(providerName);
            if (provider != null)
            {
                provider.Configure(settings);
                _logger.LogInformation("Configured provider {ProviderName}", providerName);
            }
        }
    }
}