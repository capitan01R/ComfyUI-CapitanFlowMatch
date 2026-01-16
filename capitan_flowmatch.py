import torch
import comfy.samplers
from comfy.k_diffusion import sampling as k_diffusion_sampling


def sample_capitan_flowmatch(model, x, sigmas, extra_args=None, callback=None, disable=None):
    extra_args = {} if extra_args is None else extra_args
    s_in = x.new_ones([x.shape[0]])
    
    for i in range(len(sigmas) - 1):
        sigma, sigma_next = sigmas[i], sigmas[i + 1]
        denoised = model(x, sigma * s_in, **extra_args)
        
        if sigma.item() > 1e-5:
            d = (x - denoised) / sigma
            x = x + d * (sigma_next - sigma)
        else:
            x = denoised
        
        if callback is not None:
            callback({'x': x, 'i': i, 'sigma': sigma, 'sigma_hat': sigma, 'denoised': denoised})
    
    return x


def sample_capitan_flowmatch_advanced(model, x, sigmas, extra_args=None, callback=None, disable=None):
    extra_args = {} if extra_args is None else extra_args
    s_in = x.new_ones([x.shape[0]])
    
    for i in range(len(sigmas) - 1):
        sigma, sigma_next = sigmas[i], sigmas[i + 1]
        denoised = model(x, sigma * s_in, **extra_args)
        
        if sigma.item() > 1e-5:
            alpha = (sigma - sigma_next) / sigma
            x = x + alpha * (denoised - x)
        else:
            x = denoised
        
        if callback is not None:
            callback({'x': x, 'i': i, 'sigma': sigma, 'sigma_hat': sigma, 'denoised': denoised})
    
    return x


def sample_capitan_flowmatch_turbo(model, x, sigmas, extra_args=None, callback=None, disable=None):
    extra_args = {} if extra_args is None else extra_args
    s_in = x.new_ones([x.shape[0]])
    
    for i in range(len(sigmas) - 1):
        sigma, sigma_next = sigmas[i], sigmas[i + 1]
        denoised = model(x, sigma * s_in, **extra_args)
        d = (x - denoised) / sigma if sigma.item() > 1e-5 else torch.zeros_like(x)
        x = x + d * (sigma_next - sigma) if sigma.item() > 1e-5 else denoised
        
        if callback is not None:
            callback({'x': x, 'i': i, 'sigma': sigma, 'sigma_hat': sigma, 'denoised': denoised})
    
    return x


class CapitanShift:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                "shift": ("FLOAT", {"default": 3.0, "min": 0.1, "max": 20.0, "step": 0.1}),
            }
        }
    
    RETURN_TYPES = ("SIGMAS",)
    CATEGORY = "sampling/custom_sampling/schedulers"
    FUNCTION = "get_sigmas"

    def get_sigmas(self, steps, shift):
        timesteps = torch.linspace(1.0, 0.0, steps + 1)
        sigmas = shift * timesteps / (1 + (shift - 1) * timesteps)
        return (sigmas,)


class CapitanShiftPresets:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "preset": ([
                    "Lumina2 (Fast)",
                    "Lumina2 (Balanced)",
                    "Lumina2 (Quality)",
                    "Z-Image-Turbo (Speed)",
                    "Z-Image-Turbo (Quality)",
                    "Flux (Fast)",
                    "Flux (Balanced)",
                    "Flux (Quality)",
                    "SD3 (Balanced)",
                    "SD3 (Quality)",
                ],),
            }
        }
    
    RETURN_TYPES = ("SIGMAS", "INT", "FLOAT")
    RETURN_NAMES = ("sigmas", "recommended_steps", "recommended_cfg")
    CATEGORY = "sampling/custom_sampling/schedulers"
    FUNCTION = "get_sigmas"

    def get_sigmas(self, preset):
        presets = {
            "Lumina2 (Fast)":           {"steps": 12, "shift": 2.0, "cfg": 2.0},
            "Lumina2 (Balanced)":       {"steps": 20, "shift": 3.0, "cfg": 2.0},
            "Lumina2 (Quality)":        {"steps": 36, "shift": 6.0, "cfg": 2.0},
            "Z-Image-Turbo (Speed)":    {"steps": 8,  "shift": 1.0, "cfg": 1.0},
            "Z-Image-Turbo (Quality)":  {"steps": 36, "shift": 6.0, "cfg": 2.0},
            "Flux (Fast)":              {"steps": 12, "shift": 2.0, "cfg": 3.5},
            "Flux (Balanced)":          {"steps": 20, "shift": 3.0, "cfg": 3.5},
            "Flux (Quality)":           {"steps": 36, "shift": 6.0, "cfg": 3.5},
            "SD3 (Balanced)":           {"steps": 24, "shift": 3.0, "cfg": 4.0},
            "SD3 (Quality)":            {"steps": 36, "shift": 5.0, "cfg": 4.0},
        }
        
        p = presets[preset]
        timesteps = torch.linspace(1.0, 0.0, p["steps"] + 1)
        sigmas = p["shift"] * timesteps / (1 + (p["shift"] - 1) * timesteps)
        
        return (sigmas, p["steps"], p["cfg"])


class CapitanLinear:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "steps": ("INT", {"default": 8, "min": 1, "max": 10000}),
            }
        }
    
    RETURN_TYPES = ("SIGMAS",)
    CATEGORY = "sampling/custom_sampling/schedulers"
    FUNCTION = "get_sigmas"

    def get_sigmas(self, steps):
        sigmas = torch.linspace(1.0, 0.0, steps + 1)
        return (sigmas,)


def register_capitan_samplers():
    samplers = ["capitan_flowmatch", "capitan_flowmatch_advanced", "capitan_flowmatch_turbo"]
    for name in samplers:
        if name not in comfy.samplers.KSampler.SAMPLERS:
            comfy.samplers.KSampler.SAMPLERS.append(name)
    
    setattr(k_diffusion_sampling, 'sample_capitan_flowmatch', sample_capitan_flowmatch)
    setattr(k_diffusion_sampling, 'sample_capitan_flowmatch_advanced', sample_capitan_flowmatch_advanced)
    setattr(k_diffusion_sampling, 'sample_capitan_flowmatch_turbo', sample_capitan_flowmatch_turbo)


register_capitan_samplers()


NODE_CLASS_MAPPINGS = {
    "CapitanShift": CapitanShift,
    "CapitanShiftPresets": CapitanShiftPresets,
    "CapitanLinear": CapitanLinear,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CapitanShift": "⚓ Capitan Shift",
    "CapitanShiftPresets": "⚓ Capitan Presets",
    "CapitanLinear": "⚓ Capitan Linear",
}
