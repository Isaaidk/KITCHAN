import { apiClient } from '../api/axios.config';
import type { OnboardingRequest } from '../../core/types/user.types';

export const onboardingService = {
    // POST: /api/v1/onboarding/
    registrarRestaurante: async (data: OnboardingRequest): Promise<any> => {
        const response = await apiClient.post('/onboarding/', data);
        return response.data;
    }
};