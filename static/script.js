const API_BASE = 'http://localhost:8000';

// Подсветка активной страницы в навигации
function setActivePage() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('nav a');

    console.log('Current path:', currentPath);

    navLinks.forEach(link => {
        const linkPath = link.getAttribute('href');
        link.classList.remove('active');

        // Make sure we're comparing exact paths, handling possible variations like index.html
        if (currentPath === linkPath ||
            (currentPath === '/' && linkPath === '/') ||
            (currentPath.includes('profiles') && linkPath === '/profiles') ||
            (currentPath.includes('history') && linkPath === '/history')) {
            link.classList.add('active');
            console.log('Active link set:', linkPath);
        }
    });
}

// Загрузка активного профиля
async function loadActiveProfile() {
    try {
        const response = await fetch(`${API_BASE}/api/profiles/`);
        if (response.ok) {
            const profiles = await response.json();
            const activeProfile = profiles.find(p => p.is_active);
            if (activeProfile && document.getElementById('active-profile-name')) {
                document.getElementById('active-profile-name').textContent = activeProfile.name;
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки активного профиля:', error);
    }
}

// Проверка статуса авторизации
async function checkAuthStatus() {
    try {
        console.log('Checking auth status...');
    } catch (error) {
        console.error('Ошибка проверки авторизации:', error);
    }
}

// Уведомления
function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    if (!notification) return;

    const text = notification.querySelector('.notification-text');
    if (!text) return;

    notification.className = `notification ${type}`;
    text.textContent = message;
    notification.classList.add('show');

    setTimeout(() => {
        notification.classList.remove('show');
    }, 5000);
}

// Модальные окна
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'flex';
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
}

// Закрытие модального окна при клике вне его
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
});

// ========== PROFILES FUNCTIONALITY ==========

// Загрузка профилей
async function loadProfiles() {
    try {
        const response = await fetch(`${API_BASE}/api/profiles/`);

        // Проверяем, что ответ является JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            throw new Error('Server returned non-JSON response');
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const profiles = await response.json();
        const grid = document.getElementById('profiles-grid');

        if (!grid) {
            console.error('Profiles grid element not found');
            return;
        }

        if (profiles.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                            <circle cx="12" cy="7" r="4"></circle>
                        </svg>
                    </div>
                    <h3>Нет созданных профилей</h3>
                    <p>Создайте первый профиль для автоматических откликов</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = profiles.map(profile => `
            <div class="profile-card ${profile.is_active ? 'active' : ''}">
                <div class="profile-header">
                    <h3 class="profile-name">${profile.name}</h3>
                    ${profile.is_active ? '<span class="active-badge">Активный</span>' : ''}
                </div>
                <p class="profile-description">${profile.description || 'Без описания'}</p>
                <div class="profile-meta">
                    <div class="meta-item">
                        <strong>Резюме:</strong> ${profile.resume_id || 'Не указано'}
                    </div>
                    <div class="meta-item">
                        <strong>Статус:</strong>
                        <span class="${profile.has_token ? 'status-accepted' : 'status-pending'}">
                            ${profile.has_token ? 'Авторизован' : 'Требуется авторизация'}
                        </span>
                    </div>
                </div>
                <div class="profile-actions">
                    ${!profile.is_active ?
                        `<button class="btn btn-select" onclick="activateProfile(${profile.id})">
                            Активировать
                        </button>` : ''
                    }
                    <button class="btn btn-outline" onclick="authorizeProfile(${profile.id})">
                        ${profile.has_token ? 'Переавторизовать' : 'Авторизовать'}
                    </button>
                    <button class="btn btn-danger" onclick="deleteProfile(${profile.id})">
                        Удалить
                    </button>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Ошибка загрузки профилей:', error);
        showNotification('Ошибка загрузки профилей: ' + error.message, 'error');
    }
}

// Создание профиля
async function createProfile() {
    const profileData = {
        name: document.getElementById('p-name')?.value || '',
        description: document.getElementById('p-desc')?.value || '',
        resume_id: document.getElementById('p-resume')?.value || '',
        bad_words: document.getElementById('p-bad')?.value || '',
        client_id: document.getElementById('p-cid')?.value || '',
        client_secret: document.getElementById('p-csec')?.value || '',
        redirect_uri: document.getElementById('p-ruri')?.value || '',
        cover_letter: document.getElementById('p-letter')?.value || ''
    };

    // Валидация
    if (!profileData.name || !profileData.client_id || !profileData.client_secret) {
        showNotification('Заполните обязательные поля: название, Client ID и Client Secret', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/profiles/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(profileData)
        });

        if (response.ok) {
            const result = await response.json();
            showNotification('Профиль успешно создан!', 'success');
            closeModal('create-profile-modal');
            clearProfileForm();
            loadProfiles();
        } else {
            const errorText = await response.text();
            showNotification(`Ошибка создания профиля: ${errorText}`, 'error');
        }
    } catch (error) {
        console.error('Ошибка создания профиля:', error);
        showNotification('Ошибка создания профиля', 'error');
    }
}

// Активация профиля
async function activateProfile(profileId) {
    try {
        const response = await fetch(`${API_BASE}/api/profiles/${profileId}/activate`, {
            method: 'POST'
        });

        if (response.ok) {
            showNotification('Профиль активирован', 'success');
            loadProfiles();
            loadActiveProfile();
        } else {
            showNotification('Ошибка активации профиля', 'error');
        }
    } catch (error) {
        console.error('Ошибка активации:', error);
        showNotification('Ошибка активации профиля', 'error');
    }
}

// Удаление профиля
async function deleteProfile(profileId) {
    if (!confirm('Вы уверены, что хотите удалить профиль?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/profiles/${profileId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('Профиль удален', 'success');
            loadProfiles();
            loadActiveProfile();
        } else {
            showNotification('Ошибка удаления профиля', 'error');
        }
    } catch (error) {
        console.error('Ошибка удаления:', error);
        showNotification('Ошибка удаления профиля', 'error');
    }
}

// Авторизация профиля
async function authorizeProfile(profileId) {
    try {
        const response = await fetch(`${API_BASE}/api/auth/link/${profileId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        // Открываем ссылку авторизации в новом окне
        const authWindow = window.open(data.url, 'hh_auth', 'width=600,height=700');

        // Слушаем сообщения от окна авторизации
        window.addEventListener('message', async function(event) {
            if (event.data && event.data.type === 'hh_auth_code') {
                const authCode = event.data.code;

                // Обмениваем код на токен
                try {
                    const tokenResponse = await fetch(`${API_BASE}/api/auth/token`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            profile_id: profileId,
                            auth_code: authCode
                        })
                    });

                    if (tokenResponse.ok) {
                        showNotification('Авторизация прошла успешно!', 'success');
                        loadProfiles();
                    } else {
                        const error = await tokenResponse.json();
                        showNotification(`Ошибка авторизации: ${error.detail || 'Неизвестная ошибка'}`, 'error');
                    }
                } catch (error) {
                    console.error('Ошибка при обмене кода на токен:', error);
                    showNotification('Ошибка при обмене кода на токен', 'error');
                }
            }
        });

    } catch (error) {
        console.error('Ошибка авторизации:', error);
        showNotification('Ошибка получения ссылки авторизации', 'error');
    }
}

// Очистка формы профиля
function clearProfileForm() {
    const fields = ['p-name', 'p-desc', 'p-resume', 'p-bad', 'p-cid', 'p-csec', 'p-ruri', 'p-letter'];
    fields.forEach(id => {
        const element = document.getElementById(id);
        if (element) element.value = '';
    });

    const redirectUri = document.getElementById('p-ruri');
    if (redirectUri) redirectUri.value = 'http://localhost:8000/static/auth_callback.html';
}

// ========== VACANCIES FUNCTIONALITY ==========

// Поиск вакансий
async function searchVacancies() {
    const searchInput = document.getElementById('search-input');
    if (!searchInput) return;

    const query = searchInput.value.trim();

    if (!query) {
        showNotification('Введите поисковый запрос', 'warning');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/vacancies?query=${encodeURIComponent(query)}`);
        if (response.ok) {
            const vacancies = await response.json();
            displayVacancies(vacancies);
        } else {
            const error = await response.json();
            showNotification(`Ошибка поиска вакансий: ${error.detail || 'Неизвестная ошибка'}`, 'error');
        }
    } catch (error) {
        console.error('Ошибка поиска вакансий:', error);
        showNotification('Ошибка поиска вакансий', 'error');
    }
}

// Отображение вакансий
function displayVacancies(vacancies) {
    const grid = document.getElementById('vacancies-grid');
    if (!grid) return;

    if (!vacancies || vacancies.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                        <circle cx="11" cy="11" r="8"></circle>
                        <path d="m21 21-4.3-4.3"></path>
                    </svg>
                </div>
                <h3>Вакансии не найдены</h3>
                <p>Попробуйте изменить поисковый запрос</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = vacancies.map(vacancy => `
        <div class="vacancy-card">
            <div class="vacancy-header">
                <h3 class="vacancy-title">${vacancy.title}</h3>
                <span class="vacancy-badge">${vacancy.type || 'Вакансия'}</span>
            </div>
            <div class="vacancy-content">
                <div class="vacancy-company">
                    <span class="company-icon">🏢</span>
                    ${vacancy.company}
                </div>
                <div class="vacancy-location">
                    <span class="location-icon">📍</span>
                    ${vacancy.area || 'Не указано'}
                </div>
                ${vacancy.salary ? `
                    <div class="vacancy-salary">${vacancy.salary}</div>
                ` : ''}
                <div class="vacancy-description">
                    ${vacancy.snippet || 'Описание не указано'}
                </div>
            </div>
            <div class="vacancy-actions">
                <button class="btn btn-primary" onclick="applyToVacancy('${vacancy.id}')">
                    Откликнуться
                </button>
                <a href="${vacancy.url || '#'}" target="_blank" class="btn btn-outline">
                    Подробнее
                </a>
            </div>
        </div>
    `).join('');
}

// Автоотклик на все вакансии
async function autoApplyToAll() {
    const searchInput = document.getElementById('search-input');
    if (!searchInput) return;

    const query = searchInput.value.trim();

    if (!query) {
        showNotification('Сначала выполните поиск вакансий', 'warning');
        return;
    }

    if (!confirm('Запустить автоотклики на все найденные вакансии?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/apply-all`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query })
        });

        if (response.ok) {
            showNotification('Автоотклики запущены! Отслеживайте прогресс в истории.', 'success');
        } else {
            const error = await response.json();
            showNotification(`Ошибка запуска автооткликов: ${error.detail || 'Неизвестная ошибка'}`, 'error');
        }
    } catch (error) {
        console.error('Ошибка автоотклика:', error);
        showNotification('Ошибка запуска автооткликов', 'error');
    }
}

// Ручной отклик на вакансию
async function applyToVacancy(vacancyId) {
    try {
        const response = await fetch(`${API_BASE}/api/apply/${vacancyId}`, {
            method: 'POST'
        });

        if (response.ok) {
            showNotification('Отклик отправлен!', 'success');
        } else {
            const error = await response.json();
            showNotification(`Ошибка отклика: ${error.detail || 'Неизвестная ошибка'}`, 'error');
        }
    } catch (error) {
        console.error('Ошибка отклика:', error);
        showNotification('Ошибка отправки отклика', 'error');
    }
}

// ========== HISTORY FUNCTIONALITY ==========

// Загрузка истории
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/api/history`);
        const history = await response.json();
        displayHistory(history);
    } catch (error) {
        console.error('Ошибка загрузки истории:', error);
        showNotification('Ошибка загрузки истории', 'error');
    }
}

// Отображение истории
// Обновленная функция для отображения истории
function displayHistory(history) {
    const tbody = document.querySelector('.history-table tbody');
    if (!tbody) return;

    if (!history || history.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="6">
                    <div class="empty-state">
                        <div class="empty-icon">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                                <circle cx="12" cy="12" r="10"></circle>
                                <line x1="12" y1="8" x2="12" y2="12"></line>
                                <line x1="12" y1="16" x2="12.01" y2="16"></line>
                            </svg>
                        </div>
                        <h4>Нет данных об откликах</h4>
                        <p>Отправьте несколько откликов, чтобы увидеть историю</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = history.map(item => `
        <tr>
            <td>${new Date(item.date).toLocaleDateString()}</td>
            <td>${item.vacancy_title}</td>
            <td>${item.company}</td>
            <td>
                <span class="status-badge status-${item.status}">
                    ${getStatusText(item.status)}
                </span>
            </td>
            <td>
                <a href="https://hh.ru/vacancy/${item.vacancy_id}" target="_blank">${item.vacancy_id}</a> <!-- Ссылка на вакансию -->
            </td>
            <td>
                <button class="btn btn-outline" onclick="viewResponseDetails(${item.id})">
                    Подробнее
                </button>
            </td>
        </tr>
    `).join('');
}

function getStatusText(status) {
    const statusMap = {
        'accepted': 'Принят',
        'pending': 'Ожидание',
        'rejected': 'Отклонен'
    };
    return statusMap[status] || status;
}

// Применение фильтров истории
async function applyHistoryFilters() {
    showNotification('Фильтры применены', 'info');
}

// Экспорт истории
async function exportHistory(format) {
    showNotification(`Экспорт в ${format.toUpperCase()} будет доступен в следующем обновлении`, 'info');
}

// ========== ЕДИНЫЙ ОБРАБОТЧИК ЗАГРУЗКИ СТРАНИЦЫ ==========

document.addEventListener('DOMContentLoaded', function() {
    console.log('Page loaded, initializing...');

    // Устанавливаем активную страницу
    setActivePage();

    // Определяем текущую страницу и загружаем соответствующие данные
    const path = window.location.pathname;
    console.log('Current path for data loading:', path);

    if (path.includes('profiles')) {
        console.log('Loading profiles...');
        loadProfiles();
    } else if (path.includes('history')) {
        console.log('Loading history...');
        loadHistory();
    } else if (path === '/' || path === '/index.html') {
        console.log('Loading main page data...');
        loadActiveProfile();
    }

    // Обработчик для поиска по Enter
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchVacancies();
            }
        });
    }
});