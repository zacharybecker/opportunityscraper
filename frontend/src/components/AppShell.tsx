import { useState } from 'react'
import {
  AppShell as MantineAppShell,
  NavLink,
  Group,
  Text,
  Burger,
  Avatar,
  Menu,
  UnstyledButton,
} from '@mantine/core'
import {
  IconDashboard,
  IconSearch,
  IconLayoutKanban,
  IconBuilding,
  IconRobot,
  IconSettings,
  IconChartBar,
  IconMessageCircle,
  IconShield,
  IconLogout,
  IconSpider,
  IconFiles,
  IconFileText,
} from '@tabler/icons-react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store'
import { useLogout } from '../hooks/useAuth'
import { NotificationBell } from './NotificationBell'

const navItems = [
  { label: 'Dashboard', icon: IconDashboard, path: '/' },
  { label: 'Opportunities', icon: IconSearch, path: '/opportunities' },
  { label: 'Pipeline', icon: IconLayoutKanban, path: '/pipeline' },
  { label: 'Proposals', icon: IconFileText, path: '/proposals' },
  { label: 'Knowledge Base', icon: IconFiles, path: '/knowledge' },
  { label: 'Company Profile', icon: IconBuilding, path: '/company' },
  { label: 'Scrapers', icon: IconSpider, path: '/scrapers' },
  { label: 'Settings', icon: IconSettings, path: '/settings' },
  { label: 'Analytics', icon: IconChartBar, path: '/analytics' },
  { label: 'Chat', icon: IconMessageCircle, path: '/chat' },
  { label: 'Admin', icon: IconShield, path: '/admin' },
]

export function AppShell({ children }: { children: React.ReactNode }) {
  const [opened, setOpened] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const user = useAuthStore((s) => s.user)
  const logout = useLogout()

  return (
    <MantineAppShell
      header={{ height: 60 }}
      navbar={{ width: 250, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <MantineAppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger opened={opened} onClick={() => setOpened(!opened)} hiddenFrom="sm" size="sm" />
            <IconRobot size={28} />
            <Text fw={700} size="lg">OpportunityScraper</Text>
          </Group>
          <Group gap="sm">
            <NotificationBell />
            <Menu shadow="md" width={200}>
              <Menu.Target>
                <UnstyledButton>
                  <Group gap="xs">
                    <Avatar radius="xl" size="sm">{user?.display_name?.[0] || user?.username?.[0] || '?'}</Avatar>
                    <Text size="sm">{user?.display_name || user?.username}</Text>
                  </Group>
                </UnstyledButton>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>{user?.role}</Menu.Label>
                <Menu.Item leftSection={<IconLogout size={14} />} onClick={logout}>
                  Logout
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </MantineAppShell.Header>

      <MantineAppShell.Navbar p="xs">
        {navItems
          .filter((item) => item.path !== '/admin' || user?.role === 'admin' || user?.is_superadmin)
          .map((item) => (
            <NavLink
              key={item.path}
              label={item.label}
              leftSection={<item.icon size={20} />}
              active={location.pathname === item.path}
              onClick={() => {
                navigate(item.path)
                setOpened(false)
              }}
            />
          ))}
      </MantineAppShell.Navbar>

      <MantineAppShell.Main>{children}</MantineAppShell.Main>
    </MantineAppShell>
  )
}
