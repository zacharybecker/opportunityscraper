import { useState } from 'react'
import { ActionIcon, Indicator, Popover, Stack, Text, Group, Badge, Button, ScrollArea } from '@mantine/core'
import { IconBell } from '@tabler/icons-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import apiClient from '../api/client'

dayjs.extend(relativeTime)

interface InAppNotification {
  id: string
  title: string
  body: string
  category: string
  link: string | null
  is_read: boolean
  opportunity_id: string | null
  created_at: string
}

export function NotificationBell() {
  const [opened, setOpened] = useState(false)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: countData } = useQuery({
    queryKey: ['unread-count'],
    queryFn: () => apiClient.get('/notifications/inbox/unread-count').then((r) => r.data),
    refetchInterval: 30000,
  })

  const { data: notifications } = useQuery({
    queryKey: ['inbox'],
    queryFn: () => apiClient.get<InAppNotification[]>('/notifications/inbox?page_size=10').then((r) => r.data),
    enabled: opened,
  })

  const markReadMutation = useMutation({
    mutationFn: (id: string) => apiClient.put(`/notifications/inbox/${id}/read`).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['unread-count'] })
      queryClient.invalidateQueries({ queryKey: ['inbox'] })
    },
  })

  const markAllReadMutation = useMutation({
    mutationFn: () => apiClient.post('/notifications/inbox/mark-all-read').then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['unread-count'] })
      queryClient.invalidateQueries({ queryKey: ['inbox'] })
    },
  })

  const unreadCount = countData?.count || 0
  const categoryColor: Record<string, string> = {
    opportunity: 'blue',
    pipeline: 'violet',
    scraper: 'cyan',
    system: 'gray',
  }

  const handleClick = (notif: InAppNotification) => {
    if (!notif.is_read) markReadMutation.mutate(notif.id)
    if (notif.link) {
      navigate(notif.link)
      setOpened(false)
    }
  }

  return (
    <Popover opened={opened} onChange={setOpened} width={360} position="bottom-end" shadow="md">
      <Popover.Target>
        <Indicator label={unreadCount} size={16} disabled={unreadCount === 0} color="red" processing>
          <ActionIcon variant="subtle" size="lg" onClick={() => setOpened(!opened)}>
            <IconBell size={20} />
          </ActionIcon>
        </Indicator>
      </Popover.Target>
      <Popover.Dropdown>
        <Group justify="space-between" mb="xs">
          <Text fw={600} size="sm">Notifications</Text>
          {unreadCount > 0 && (
            <Button size="xs" variant="subtle" onClick={() => markAllReadMutation.mutate()}>
              Mark all read
            </Button>
          )}
        </Group>
        <ScrollArea h={300}>
          <Stack gap="xs">
            {notifications?.map((n: InAppNotification) => (
              <div
                key={n.id}
                onClick={() => handleClick(n)}
                style={{
                  cursor: n.link ? 'pointer' : 'default',
                  padding: '8px',
                  borderRadius: '4px',
                  backgroundColor: n.is_read ? 'transparent' : 'var(--mantine-color-blue-0)',
                }}
              >
                <Group gap="xs" justify="space-between">
                  <Badge size="xs" color={categoryColor[n.category] || 'gray'}>{n.category}</Badge>
                  <Text size="xs" c="dimmed">{dayjs(n.created_at).fromNow()}</Text>
                </Group>
                <Text size="sm" fw={n.is_read ? 400 : 600} lineClamp={2}>{n.title}</Text>
              </div>
            ))}
            {!notifications?.length && (
              <Text size="sm" c="dimmed" ta="center" py="lg">No notifications</Text>
            )}
          </Stack>
        </ScrollArea>
      </Popover.Dropdown>
    </Popover>
  )
}
